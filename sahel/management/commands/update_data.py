from django.core.management.base import BaseCommand
from django.db.models import Q

from hdx.utilities.easy_logging import setup_logging
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from dateutil import parser
import pandas as pd
import numpy as np
from ...models import RegularDataset, Variable, MeasuredDataPoint, Source, Element
from datetime import datetime, timezone, date
import time
from pathlib import Path
from dotenv import load_dotenv
from unidecode import unidecode

admin1s = ["Gao", "Kidal", "Mopti", "Tombouctou", "Ménaka"]


def download_from_hdx(hdx_identifier, last_updated_date, resource_number=0):
    setup_logging()
    Configuration.create(hdx_site="prod", user_agent="SAMRA", hdx_read_only=True)
    dataset = Dataset.read_from_hdx(hdx_identifier)
    dataset_last_modified = parser.parse(dataset.get("last_modified"))
    print(dataset_last_modified.timestamp())
    print(last_updated_date.timestamp())
    if dataset_last_modified.timestamp() > last_updated_date.timestamp():
        resources = Dataset.get_all_resources([dataset])
        df = pd.read_csv(resources[resource_number].get("url"), skiprows=[1])
    else:
        print("already up to date")
        df = None
    return df


def update_wfp_price_data():
    regulardataset = RegularDataset.objects.get(pk=1)
    serve_locally = True
    if serve_locally:
        df = pd.read_csv("data/wfp_food_prices_mli.csv", skiprows=[1])
    else:
        df = download_from_hdx(regulardataset.hdx_identifier, regulardataset.last_updated_date, regulardataset.hdx_resource_number)
        regulardataset.last_updated_date = datetime.now(timezone.utc)
        regulardataset.save()

    if df is None:
        return

    df = df[df["admin1"].isin(admin1s)]
    df["price"] = df["price"].replace({0: np.nan})

    elements = Variable.objects.filter(vam_commodity__isnull=False)

    objs = []
    for element in elements:
        print(element)
        dff = df[df["commodity"] == element.vam_commodity]
        unit = dff["unit"].drop_duplicates()
        if len(unit) > 1:
            raise Exception(f"multiple units of measurement for {element.vam_commodity}")

        for _, row in dff.iterrows():
            objs.append(MeasuredDataPoint(
                element=element,
                date=row["date"],
                admin1=row["admin1"],
                admin2=row["admin2"],
                market=row["market"],
                source=regulardataset.source,
                value=row["price"],
            ))

    MeasuredDataPoint.objects.filter(source=regulardataset.source).delete()
    MeasuredDataPoint.objects.bulk_create(objs)

    source = regulardataset.source

    MeasuredDataPoint.objects.filter(source=source, date=date(2020, 5, 15), element_id=62).delete()
    MeasuredDataPoint.objects.filter(source=source, date=date(2020, 5, 15), element_id=63).delete()
    MeasuredDataPoint.objects.filter(source=source, date=date(2020, 5, 15), element_id=42).delete()


def update_dm_suividesprix():
    # only for serving locally
    # needs rewrite to not iterate over df multiple times, this is probably pretty slow
    df = pd.read_excel("data/Formulaire de suivi des prix du bétail.xlsx")
    df["Date de collecte"] = pd.to_datetime(df["Date de collecte"])
    df = df.drop([3])
    source = Source.objects.get(pk=3)
    objs = []

    # convert to numerical
    substring = "Disponibilité des aliments sur le marché"
    avg_cols = [col for col in df.columns if substring in col]
    for col in avg_cols:
        df[col] = df[col].apply(
            lambda
                value: 0.0 if value == "Mauvaise" else 0.5 if value == "Moyenne" else 1.0 if value == "Bonne" else None)

    # groupby quarter
    df = df.groupby(["Région ", "Cercle ", pd.Grouper(key="Date de collecte", freq="QS")]).mean().reset_index()
    df["date"] = df["Date de collecte"].apply(lambda value: value + pd.DateOffset(months=2, days=14))

    # prix de bovin
    element = Variable.objects.get(pk=42)
    include_substrings = [
        "Taurillon moins de 2 ans",
        "Taureau de + 2 ans",
        "Génisse de – 2 ans",
        "Vache de + 2 ans",
        "Vache reformée",
    ]
    avg_cols = [col for col in df.columns if any(substring in col for substring in include_substrings)]
    for _, row in df.iterrows():
        print(row["Région "])
        print(row[avg_cols].mean())
        objs.append(MeasuredDataPoint(
            element=element,
            source=source,
            value=row[avg_cols].mean(),
            date=row["date"],
            admin1=row["Région "].capitalize(),
            admin2=row["Cercle "].capitalize()
        ))

    # prix alimentation
    element = Variable.objects.get(pk=37)
    include_substrings = [
        "Tourteau de coton (sac de 50kg)",
        "Aliment industriel (Buna Fama, etc..) sac 50kg",
        "Son de blé (sac de 50 Kg)",
        "Son de Maïs (sac de 50 Kg)",
        "Son de mil (sac de 50 Kg)",
        "Son de Riz (sac de 50 Kg)",
    ]
    avg_cols = [col for col in df.columns if any(substring in col for substring in include_substrings)]
    for _, row in df.iterrows():
        print(row["Région "])
        print(row[avg_cols].mean())
        objs.append(MeasuredDataPoint(
            element=element,
            source=source,
            value=row[avg_cols].mean() / 50.0,
            date=row["date"],
            admin1=row["Région "].capitalize(),
            admin2=row["Cercle "].capitalize()
        ))

    # disponibilité alimentation
    element = Variable.objects.get(pk=125)
    substring = "Disponibilité des aliments sur le marché"
    avg_cols = [col for col in df.columns if substring in col]
    for _, row in df.iterrows():
        print(row["Région "])
        print(row[avg_cols].mean())
        objs.append(MeasuredDataPoint(
            element=element,
            source=source,
            value=row[avg_cols].mean(),
            date=row["date"],
            admin1=row["Région "].capitalize(),
            admin2=row["Cercle "].capitalize()
        ))

    MeasuredDataPoint.objects.filter(source=source).delete()
    MeasuredDataPoint.objects.bulk_create(objs)


def update_dm_globallivestock():
    df = pd.read_excel("data/Livestock Risk Monitoring.xlsx")
    df = df[df["Introduction : Country"] == "Mali"]
    df["admin1"] = df["Introduction : Admin Level 1"].apply(lambda admin1 : admin1.removesuffix(" (Mali)"))
    admin1s = ["Tombouctou", "Gao", "Kidal", "Mopti"]
    df = df[df["admin1"].isin(admin1s)]
    df["date"] = pd.to_datetime(df["Introduction : Which period are you reporting for (choose any date from the relevant quarter)"])
    df["admin2"] = df["Introduction : Admin Level 2"]

    multicol_elements = Variable.objects.filter(dm_globalform_fieldgroup__isnull=False)
    for element in multicol_elements:
        high_field = f"{element.dm_globalform_fieldgroup} : {element.dm_globalform_group_highfield}"
        mid_field = f"{element.dm_globalform_fieldgroup} : {element.dm_globalform_group_midfield}"
        low_field = f"{element.dm_globalform_fieldgroup} : {element.dm_globalform_group_lowfield}"
        df[element.pk] = (df[high_field].fillna(0) + df[mid_field].fillna(0) * 0.5 + df[low_field].fillna(0) * 0.0) / 100

    singlecol_elements = Variable.objects.filter(dm_globalform_field__isnull=False)
    for element in singlecol_elements:
        qual2quant = {element.dm_globalform_field_highvalue: 1.0,
                      element.dm_globalform_field_midvalue: 0.5,
                      element.dm_globalform_field_lowvalue: 0.0}
        df[element.pk] = df[element.dm_globalform_field].apply(lambda qual: qual2quant.get(qual))

    df = pd.melt(df, id_vars=["date", "admin1", "admin2"],
                 value_vars=[element.pk for element in (multicol_elements | singlecol_elements).distinct()])
    print(df)
    df = df.groupby(["variable", "admin1", "admin2", pd.Grouper(key="date", freq="QS")]).mean().reset_index()
    df["date"] = df["date"] + pd.DateOffset(months=2, days=14)
    print(df)

    source = Source.objects.get(pk=4)

    objs = [MeasuredDataPoint(
        element_id=row.variable,
        source=source,
        value=row.value,
        date=row.date,
        admin1=row.admin1,
        admin2=row.admin2,
    ) for row in df.itertuples()]

    MeasuredDataPoint.objects.filter(source=source).delete()
    MeasuredDataPoint.objects.bulk_create(objs)

    # delete problem points



def update_acled():
    source = Source.objects.get(pk=6)
    df = pd.read_csv("data/2019-08-06-2022-08-11-Mali.csv")
    print(df.columns)
    print(type(df["event_date"].iloc[0]))
    print(df["admin1"].unique())

    df = df.replace("Menaka", "Ménaka")
    df = df[df["admin1"].isin(admin1s)]
    df["date"] = pd.to_datetime(df["event_date"], format="%d %B %Y")
    df["number_events"] = 1
    df = df.groupby(["admin1", "admin2", pd.Grouper(key="date", freq="MS")]).sum().reset_index()
    df["date"] += pd.DateOffset(days=14)
    df = df[df["date"] < "2022-08-01"]

    print(df)

    objs = [measureddatapoint for _, row in df.iterrows() for measureddatapoint in
            [MeasuredDataPoint(
                element_id=156,
                source=source,
                date=row["date"],
                value=row["number_events"],
                admin1=row["admin1"],
                admin2=row["admin2"],
            ), MeasuredDataPoint(
                element_id=157,
                source=source,
                date=row["date"],
                value=row["fatalities"],
                admin1=row["admin1"],
                admin2=row["admin2"],
            )]]

    MeasuredDataPoint.objects.filter(source=source).delete()
    MeasuredDataPoint.objects.bulk_create(objs)


def update_ndvi():
    source = Source.objects.get(pk=7)
    admin1_files = (
        ("Mali - Gao_Pasture_", "Gao"),
        ("Mali - Kidal__", "Kidal"),
        ("Mali - Mopti_Pasture_", "Mopti"),
        ("Mali - Tombouctou_Pasture_", "Tombouctou")
    )
    objs = []
    for admin1_file in admin1_files:
        for measure in ["NDVI-", "Rainfall"]:
            element_ids = [169, 170] if measure == "Rainfall" else [171, 172]
            for year in range(2012, 2023):
                if not (year == 2022 and admin1_file[1] == "Gao" and measure == "Rainfall"):
                    pass
                df = pd.read_csv(f"data/wfp seasonal explorer/{admin1_file[0]}{measure}{year}.csv")
                df["Day"] = df["Dekad"] * 10 - 5
                df["date"] = pd.to_datetime(df[["Year", "Month", "Day"]])
                df = df.dropna()
                real_column = "NDVI" if measure == "NDVI-" else "Rainfall (mm)"
                avg_column = "Average" if measure =="NDVI-" else "Average (mm)"
                for _, row in df.iterrows():
                    objs.append(MeasuredDataPoint(
                        element_id=element_ids[0],
                        source=source,
                        value=row[real_column],
                        date=row["date"],
                        admin1=admin1_file[1],
                    ))
                    objs.append(MeasuredDataPoint(
                        element_id=element_ids[1],
                        source=source,
                        value=row[avg_column],
                        date=row["date"],
                        admin1=admin1_file[1],
                    ))

    MeasuredDataPoint.objects.filter(source=source).delete()
    MeasuredDataPoint.objects.bulk_create(objs)


def read_ven_producerprices():
    element_id = 212
    source_id = 9
    df = pd.read_csv("data/producer-prices_ven.csv", skiprows=[1])
    df = df[(df["Item"] == "Cocoa beans") & (df["Unit"] == "USD")][["Year", "Value"]]
    MeasuredDataPoint.objects.filter(source_id=source_id).delete()
    MeasuredDataPoint.objects.bulk_create([
        MeasuredDataPoint(
            element_id=element_id,
            source_id=source_id,
            value=row["Value"],
            date=date(int(row["Year"]), 7, 1)
        )
        for _, row in df.iterrows()
    ])


class Command(BaseCommand):
    def handle(self, *args, **options):
        # update_wfp_price_data()
        # update_dm_suividesprix()
        # update_dm_globallivestock()
        # update_acled()
        # update_ndvi()
        read_ven_producerprices()
        pass