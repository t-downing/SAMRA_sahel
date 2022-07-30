from django.core.management.base import BaseCommand
from django.db.models import Q

from hdx.utilities.easy_logging import setup_logging
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from dateutil import parser
import pandas as pd
from ...models import RegularDataset, Element, MeasuredDataPoint, Source
from datetime import datetime, timezone
import time


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


def update_dm_data():
    # only for serving locally
    df = pd.read_excel("data/Formulaire de suivi des prix du bétail.xlsx")
    df["Date de collecte"] = pd.to_datetime(df["Date de collecte"])
    df = df.drop([3])
    element = Element.objects.get(label="Prix de bovin")
    source = Source.objects.get(title="Formulaire de suivi des prix du bétail")
    include_substrings = [
        "Taurillon moins de 2 ans",
        "Taureau de + 2 ans",
        "Génisse de – 2 ans",
        "Vache de + 2 ans",
        "Vache reformée",
    ]
    avg_cols = [col for col in df.columns if any(substring in col for substring in include_substrings)]
    print(df["Date de collecte"].dtypes)
    objs = []
    for _, row in df.iterrows():
        print(row["Région "])
        print(row[avg_cols].mean())
        objs.append(MeasuredDataPoint(
            element=element,
            source=source,
            value=row[avg_cols].mean(),
            date=row["Date de collecte"],
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

    elements = Element.objects.filter(
        Q(dm_globalform_fieldgroup__isnull=False)
    )

    objs = []
    for element in elements:
        df["value"] = df[[element.dm_globalform_field_good, element.dm_globalform_field_ok]]


class Command(BaseCommand):
    def handle(self, *args, **options):
        # update_wfp_price_data()
        # update_dm_data()
        update_dm_globallivestock()