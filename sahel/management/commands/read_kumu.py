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

        # ELEMENTS
        for k_element in kumu_project.get("elements"):
            break
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

        # CONNECTIONS
        k_id2pk = {
            element.kumu_id: element.pk
            for element in Element.objects.all()
        }
        for k_conn in kumu_project.get("connections"):
            break
            print(k_conn.get("from"))
            from_pk = k_id2pk.get(k_conn.get("from"))
            to_pk = k_id2pk.get(k_conn.get("to"))
            if None not in [from_pk, to_pk]:
                try:
                    conn = ElementConnection.objects.get(from_element_id=from_pk, to_element_id=to_pk)
                except ElementConnection.DoesNotExist:
                    conn = ElementConnection(from_element_id=from_pk, to_element_id=to_pk)
                conn.save()

        # POSITIONS
        target_map = 1
        samramodel_pk = 2
        shrink_factor = 0.7
        x_shift, y_shift = 5000, 0
        story_pk = SamraModel.objects.get(pk=samramodel_pk).default_story_id
        objs = []
        for k_pos in kumu_project.get("maps")[target_map].get("elements"):
            pprint(k_pos)
            if k_pos.get("pinned"):
                pk = k_id2pk.get(k_pos.get("element"))
                if pk is not None:
                    pos, _ = ElementPosition.objects.get_or_create(
                        element_id=pk,
                        story_id=story_pk
                    )
                    pos.x_pos = k_pos.get("position")["x"] * 0.7 + x_shift
                    pos.y_pos = k_pos.get("position")["y"] * 0.7 + y_shift
                    objs.append(pos)
        ElementPosition.objects.bulk_update(objs, ["x_pos", "y_pos"])
