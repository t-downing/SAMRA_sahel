from django.core.management.base import BaseCommand
from django.db.models import Q

from hdx.utilities.easy_logging import setup_logging
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from dateutil import parser
import pandas as pd
import numpy as np
from ...models import RegularDataset, Variable, MeasuredDataPoint, Source, Element, HouseholdConstantValue
from datetime import datetime, timezone, date
import time
from pathlib import Path
from dotenv import load_dotenv
from unidecode import unidecode
from itertools import chain

MALI_ADMIN1S = ["Gao", "Kidal", "Mopti", "Tombouctou", "Ménaka"]
MRT_ADMIN1 = 'Hodh Ech Chargi'
MRT_ADMIN2 = 'Bassikounou'
DAYS_IN_MONTH = 30.437


# HDX
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


# WFP
def update_mali_wfp_price_data():
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

    df = df[df["admin1"].isin(MALI_ADMIN1S)]
    df["price"] = df["price"].replace({0: np.nan})
    df = df.dropna()

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
                admin0='Mali',
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
    MeasuredDataPoint.objects.filter(source=source, date=date(2020, 5, 15), element_id=131).delete()


def update_mrt_wfp():
    # TODO: consolidate with other VAM function
    # TODO: actually set up proper automation
    mrt_adm1s = ['Hodh Ech Chargi']
    mrt_adm2s = ['Bassikounou']
    df = pd.read_csv('data/wfp_food_prices_mrt.csv', skiprows=[1])
    df = df[(df['admin1'].isin(mrt_adm1s) & df['admin2'].isin(mrt_adm2s))]
    df["price"] = df["price"].replace({0: np.nan})
    df = df.dropna()
    print(f'{len(df)} data points')

    elements = Variable.objects.filter(vam_commodity__isnull=False)
    objs = []
    for element in elements:
        dff = df[df["commodity"] == element.vam_commodity]
        unit = dff["unit"].drop_duplicates()
        if len(unit) > 1:
            raise Exception(f"multiple units of measurement for {element.vam_commodity}")

        print(f"{element.label}: {len(dff)} data points")

        for _, row in dff.iterrows():
            objs.append(MeasuredDataPoint(
                element=element,
                date=row["date"],
                admin0="Mauritanie",
                admin1=row["admin1"],
                admin2=row["admin2"],
                market=row["market"],
                source_id=11,
                value=row["price"],
            ))

    MeasuredDataPoint.objects.filter(source_id=11).delete()
    MeasuredDataPoint.objects.bulk_create(objs)


# BKN other
def update_mrt_prixmarche():
    alimentation_pks = [248, 249, 250]
    markets = (
        ('Bassikounou', 'BDD PM_BKN'),
        ('Fassala', 'BDD PM_fass'),
        ('Akor', 'BDD PM_Akor'),
        ('Gneibe', 'BDD PM_Gneibe'),
        ('Mberra', 'BDD PM_CpMberra'),
    )
    skiprange = list(chain(range(7), range(46, 100)))
    df_all = pd.DataFrame()
    for market in markets:
        df = pd.read_excel('data/2_1_ BDD sur les prix Marché_ BKN.xls', sheet_name=market[1], skiprows=skiprange)
        df = df.set_index('Aliment de base')
        df = df.transpose()
        df['date'] = pd.date_range(start='2022-01-01', periods=24, freq='MS')
        df = pd.melt(df, id_vars=['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df["value"] = df["value"].replace({0: np.nan})
        df = df.dropna()
        df['date'] = df['date'] + pd.DateOffset(months=2, days=14)
        df['market'] = market[0]
        df_all = pd.concat([df_all, df])
    print(df_all['Aliment de base'].unique())
    objs = []
    variables = Variable.objects.filter(mrt_prixmarche_name__isnull=False)
    for variable in variables:
        dff = df_all[df_all['Aliment de base'] == variable.mrt_prixmarche_name]
        unit = 50.0 if variable.pk in alimentation_pks else 1.0
        print(f"{variable.label}: {len(dff)} data points")
        for _, row in dff.iterrows():
            objs.append(MeasuredDataPoint(
                element_id=variable.pk,
                date=row["date"],
                admin0="Mauritanie",
                admin1='Hodh Ech Chargui',
                admin2='Bassikounou',
                market=row["market"],
                value=row["value"]/unit,
                source_id=12,
            ))
    MeasuredDataPoint.objects.filter(source_id=12).delete()
    MeasuredDataPoint.objects.bulk_create(objs)


# DM
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
            admin0='Mali',
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
    df = df.groupby(["variable", "admin1", "admin2", pd.Grouper(key="date", freq="QS")]).mean().reset_index()
    df["date"] = df["date"] + pd.DateOffset(months=2, days=14)
    df = df.dropna()
    print(df)

    source = Source.objects.get(pk=4)

    objs = [MeasuredDataPoint(
        element_id=row.variable,
        source=source,
        value=row.value,
        date=row.date,
        admin0='Mali',
        admin1=row.admin1,
        admin2=row.admin2,
    ) for row in df.itertuples()]

    MeasuredDataPoint.objects.filter(source=source).delete()
    MeasuredDataPoint.objects.bulk_create(objs)

    # delete problem points


def update_dm_phm_bkn_maraichange():
    df = pd.read_excel("data/MRT - PHM Maraichage 2023.xlsx")
    source_pk = 15
    admin0 = 'Mauritanie'
    admin1 = MRT_ADMIN1
    admin2 = MRT_ADMIN2

    # sections and options
    DATE = "Date"
    PROFIL = 'Profil du ménage : '
    NOMBRE_PER = PROFIL + 'Nombre de personnes totales dans le ménage'
    CULT_ET_REND = 'Cultures et rendements : '
    REND_ET_PERTE = CULT_ET_REND + 'Rendements et pertes-post récolte : '
    SUPERFICIE = REND_ET_PERTE + 'Quelle superficie de terre avez-vous cultivée pour cette culture au cours de la dernière saison avec les semences distribuées par le CICR? (metre carré'
    QUANT_PROD = REND_ET_PERTE + 'Quelle superficie de terre avez-vous cultivée pour cette culture au cours de la dernière saison avec les semences distribuées par le CICR? (mètre carré'
    CONS = REND_ET_PERTE + 'Stock pour la consommation du ménage'
    VEND = REND_ET_PERTE + 'Vendue'
    DETTE_AG = REND_ET_PERTE + 'Remboursement de la dette liée à la production agricole (y compris la location des terres et les intrants agricoles)'
    DETTE_AUTRE = REND_ET_PERTE + "Remboursement d'autres dettes"
    STOCK = REND_ET_PERTE + "Stock de semences pour la prochaine saison"
    DON = REND_ET_PERTE + "Donation"
    AUTRE = REND_ET_PERTE + "Autre"
    PERTE = REND_ET_PERTE + "Avez-vous eu des pertes après la récolte ?"
    PERTE_FRAC = REND_ET_PERTE + "Si oui, pouvez-vous estimer la proportion de votre récolte?"
    PERTE_FRAC_VALUES = {
        "Une petite partie (25%)": 0.25,
        "La moitié (50%)": 0.5,
        "La plus grande partie (75%)": 0.75,
        "La totalité (100%)": 1.0,
    }
    FREQ = REND_ET_PERTE + "À quelle fréquence vendez-vous cette culture?"
    FREQ_VALUES = {
        "Weekly": 7,
        "Daily": 1,
        "Monthly": DAYS_IN_MONTH
    }
    QUANT_VENDU = REND_ET_PERTE + "En moyenne, quelle quantité vendez-vous par marché ? (en KILOS)"
    REVENU = REND_ET_PERTE + "En général, la vente de la récolte de cette culture vous rapporte combien par marché ?"
    MARCHE_ET_VENTE = "Marché et vente des produits : "
    TRANS = MARCHE_ET_VENTE + "Quel est le cout éventuel du transport ?"
    PRIX_TRANS = MARCHE_ET_VENTE + "Si argent, combien par trajet ? (aller/retour)"
    RIEN = "Rien"
    NO = "no"

    df = df.replace({
        PERTE_FRAC: PERTE_FRAC_VALUES,
        FREQ: FREQ_VALUES,
        SUPERFICIE: {0: np.nan}
    })

    df[DATE] = pd.to_datetime(df[DATE])
    df[PRIX_PER_KG := "prix_per_kg"] = df[REVENU] / df[QUANT_VENDU]
    df[PERTE_FRAC] = df.apply(lambda row: 0 if row[PERTE] == NO else row[PERTE_FRAC], axis=1)
    df[PRIX_TRANS] = df.apply(lambda row: 0 if row[TRANS] == RIEN else row[PRIX_TRANS], axis=1)
    df[COUT_TRANS_PER_KG := 'cout_trans_per_kg'] = df[PRIX_TRANS] / df[QUANT_VENDU]
    df[SUPERFICIE] /= 10000
    df[RENDEMENT := 'rendement'] = df[QUANT_PROD] / df[SUPERFICIE]
    frac_cols = [CONS, VEND, DETTE_AG, DETTE_AUTRE, STOCK, DON, AUTRE]
    df[frac_cols] /= 100

    timeseries_cols = [PRIX_PER_KG, PERTE_FRAC, COUT_TRANS_PER_KG]
    constant_cols = [*frac_cols, NOMBRE_PER, RENDEMENT, SUPERFICIE]

    dff = df[[DATE, *timeseries_cols]]
    dff = dff.groupby(pd.Grouper(key=DATE, freq="QS")).mean().reset_index()
    dff = dff.dropna()
    dff[DATE] = dff[DATE] + pd.DateOffset(months=1, days=14)

    # timeseries inputs
    print(dff)
    objs = []
    pk2col = {
        267: PRIX_PER_KG,
        268: COUT_TRANS_PER_KG,
        269: PERTE_FRAC,
    }

    objs.extend([
        MeasuredDataPoint(
            element_id=pk,
            value=row[col_name],
            date=row[DATE],
            admin0=admin0,
            admin1=admin1,
            admin2=admin2,
            source_id=source_pk
        )
        for pk, col_name in pk2col.items()
        for _, row in dff.iterrows()
    ])

    MeasuredDataPoint.objects.filter(source_id=source_pk).delete()
    MeasuredDataPoint.objects.bulk_create(objs)

    # one-off inputs
    dff = df[constant_cols]
    dff = dff.mean()
    print(dff)
    pk2col = {
        270: CONS,
        271: VEND,
        272: DETTE_AG,
        273: DETTE_AUTRE,
        274: STOCK,
        275: DON,
        276: AUTRE,
        138: NOMBRE_PER,
        277: RENDEMENT,
        278: SUPERFICIE
    }

    objs.extend([
        HouseholdConstantValue(
            element_id=pk,
            value=dff[col_name],
            admin0=admin0,
            admin1=admin1,
            admin2=admin2,
            source_id=source_pk,
        )
        for pk, col_name in pk2col.items()
    ])

    HouseholdConstantValue.objects.filter(source_id=source_pk).delete()
    HouseholdConstantValue.objects.bulk_create(objs)


# other 3rd party
def update_acled():
    source = Source.objects.get(pk=6)
    df = pd.read_csv("data/2019-08-06-2022-08-11-Mali.csv")
    print(df.columns)
    print(type(df["event_date"].iloc[0]))
    print(df["admin1"].unique())

    df = df.replace("Menaka", "Ménaka")
    df = df[df["admin1"].isin(MALI_ADMIN1S)]
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


def update_ndvi(admin0):
    source = Source.objects.get(pk=7)
    admin1_files = None
    admin2 = None
    min_year = None
    if admin0 == 'Mali':
        admin1_files = (
            ("Mali - Gao_Pasture_", "Gao"),
            ("Mali - Kidal__", "Kidal"),
            ("Mali - Mopti_Pasture_", "Mopti"),
            ("Mali - Tombouctou_Pasture_", "Tombouctou")
        )
        min_year = 2012
    elif admin0 == 'Mauritanie':
        admin1_files = (
            ("Mauritania - Hodh Ech Chargi - Bassikounou__", "Hodh Ech Chargi"),
        )
        admin2 = 'Bassikounou'
        min_year = 2015
    objs = []
    for admin1_file in admin1_files:
        for measure in ["NDVI-", "Rainfall"]:
            element_ids = [169, 170] if measure == "Rainfall" else [171, 172]
            for year in range(min_year, 2023):
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
                        admin0=admin0,
                        admin1=admin1_file[1],
                        admin2=admin2,
                    ))
                    objs.append(MeasuredDataPoint(
                        element_id=element_ids[1],
                        source=source,
                        value=row[avg_column],
                        date=row["date"],
                        admin0=admin0,
                        admin1=admin1_file[1],
                        admin2=admin2,
                    ))

    MeasuredDataPoint.objects.filter(source=source, admin0=admin0).delete()
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
        # update_mali_wfp_price_data()
        update_dm_suividesprix()
        update_dm_globallivestock()
        # update_acled()
        # update_ndvi('Mauritanie')
        # read_ven_producerprices()
        # update_mrt_wfp()
        # update_mrt_prixmarche()
        # update_dm_phm_bkn_maraichange()
        pass