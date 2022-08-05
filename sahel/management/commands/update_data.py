from django.core.management.base import BaseCommand
from django.db.models import Q

from hdx.utilities.easy_logging import setup_logging
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from dateutil import parser
import pandas as pd
import numpy as np
from ...models import RegularDataset, Element, MeasuredDataPoint, Source
from datetime import datetime, timezone, date
import time

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

    elements = Element.objects.filter(vam_commodity__isnull=False)

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
    element = Element.objects.get(pk=42)
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
    element = Element.objects.get(pk=37)
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
    element = Element.objects.get(pk=125)
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

    multicol_elements = Element.objects.filter(dm_globalform_fieldgroup__isnull=False)
    for element in multicol_elements:
        high_field = f"{element.dm_globalform_fieldgroup} : {element.dm_globalform_group_highfield}"
        mid_field = f"{element.dm_globalform_fieldgroup} : {element.dm_globalform_group_midfield}"
        low_field = f"{element.dm_globalform_fieldgroup} : {element.dm_globalform_group_lowfield}"
        df[element.pk] = (df[high_field].fillna(0) + df[mid_field].fillna(0) * 0.5 + df[low_field].fillna(0) * 0.0) / 100

    singlecol_elements = Element.objects.filter(dm_globalform_field__isnull=False)
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


def fix_problem_data_points():
    points = MeasuredDataPoint.objects.filter(source_id=1, date=date(2020, 5, 15), element_id=131)
    points.delete()


class Command(BaseCommand):
    def handle(self, *args, **options):
        # update_wfp_price_data()
        # update_dm_suividesprix()
        # update_dm_globallivestock()
        fix_problem_data_points()