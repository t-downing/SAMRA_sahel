from django.core.management.base import BaseCommand
from sahel.models import *
import json
from pprint import pprint


class Command(BaseCommand):
    def handle(self, *args, **options):
        regions_dict = {
            region.name: region.pk
            for region in Region.objects.all()
        }
        status_dict = {
            "Good": SituationalAnalysis.SA_STATUS_GOOD,
            "Medium": SituationalAnalysis.SA_STATUS_OK,
            "Bad": SituationalAnalysis.SA_STATUS_BAD
        }
        trend_dict = {
            "Improving": SituationalAnalysis.SA_TREND_IMPROVING,
            "Stagnant": SituationalAnalysis.SA_TREND_STAGNANT,
            "Worsening": SituationalAnalysis.SA_TREND_WORSENING,
        }
        sectors_dict = {
            sector.name: sector.pk
            for sector in Sector.objects.all()
        }
        sector_type_dict = {
            "Formal Sector": Element.FORMAL_SECTOR,
            "Informal Sector": Element.INFORMAL_SECTOR,
        }
        path = "data/kumu-ebecq-venezuela-systems-map-draft-september-2022.json"
        with open(path) as json_file:
            kumu_project = json.load(json_file)

        for k_element in kumu_project.get("elements"):
            k_data = k_element.get("attributes")
            print(k_data.get("label"))
            k_status = k_data.get("1 - functionality status")
            k_trend = k_data.get("2 - functionality trend")
            k_tags = k_data.get("tags")
            k_id = k_element.get("_id")
            k_type = k_data.get("element type")
            region_pks = []
            sector_pks = []
            sector_type = None
            element = None
            if k_tags is not None:
                for region in ["VCO", "PUO", "SCI"]:
                    if region in k_tags:
                        region_pks.append(regions_dict.get(region))
                for sector in sectors_dict:
                    if sector in k_tags:
                        sector_pks.append(sectors_dict.get(sector))
                for sector_type_key in sector_type_dict:
                    if sector_type_key in k_tags:
                        sector_type = sector_type_dict.get(sector_type_key)
            if k_type == "Situational Analysis":
                try:
                    element = SituationalAnalysis.objects.get(kumu_id=k_id)
                    print("found SA")
                except SituationalAnalysis.DoesNotExist:
                    element = SituationalAnalysis(
                        kumu_id=k_id,
                        label=k_data.get("label"),
                        element_type=SituationalAnalysis.SITUATIONAL_ANALYSIS,
                    )
                    print("created SA")
                element.status = status_dict.get(k_status)
                element.trend = trend_dict.get(k_trend)
            elif k_type == "Proposed Recommendations":
                try:
                    element = TheoryOfChange.objects.get(kumu_id=k_id)
                    print("found TC")
                except TheoryOfChange.DoesNotExist:
                    element = TheoryOfChange(
                        kumu_id=k_id,
                        label=k_data.get("label"),
                        element_type=TheoryOfChange.INTERVENTION,
                    )
                    print("created TC")
            elif k_type == "Shock":
                try:
                    element = ShockStructure.objects.get(kumu_id=k_id)
                    print("found SE")
                except ShockStructure.DoesNotExist:
                    element = ShockStructure(
                        kumu_id=k_id,
                        label=k_data.get("label"),
                        element_type=ShockStructure.SHOCK,
                    )
                    print("created SE")
            if element is not None:
                element.samramodel_id = 2
                element.description = k_data.get("description")
                element.sector_type = sector_type
                element.save()
                element.sectors.add(*sector_pks)
                element.regions.add(*region_pks)

            pass
