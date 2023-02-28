from django.core.management.base import BaseCommand
from sahel.models import *
from datetime import date
from sahel.sd_model.forecasting import forecast_element


class Command(BaseCommand):
    def handle(self, *args, **options):
        name_pks = (
            ('Blé', 130),
            ('Petit mil ', 230),
            ('Riz importé ', 54),
            ('Riz local', 55),
            ('Huile ', 58),
            ('Thé', None),
            ('Sucre', 60),
            ('Lait en poudre(selia)', 61),
            ('lait concentré non sucré(gloria)', None),
            ('Haricot (Niébé)', None),
            ('Légumes', None),
            ('Oignon violet de galmi', None),
            ('Oignons blanc', None),
            ('Pomme de terre', None),
            ('Gombo frais', None),
            ('Gombo sec', None),
            ('Chou', None),
            ('Aubergine', None),
            ('Carotte ', None),
            ('Patate douce', None),
            ('Viande et cheptel vif', None),
            ('Viande bovine', 64),
            ('Viande petit ruminant (Caprin)', 65),
            ('Viande petit ruminant(ovin)', 66),
            ('Caprin moins un an', None),
            ('Caprin adulte >1an', 63),
            ('Mouton jeune moins un an', None),
            ('Mouton adulte plus de 1 an', 62),
            ('Bovin jeun ', None),
            ('Bovin adulte', 42),
            ('Tourteau de coton (Rakkal)', None),
            ('Son de blé', None),
            ('La Paille', None),
            ('Poule', None),
            ('Coq', None),
            ('Poulet surgelait(cuisse)', None)
        )
        # for name_pk in name_pks:
        #     if name_pk[1] is not None:
        #         variable = Variable.objects.get(pk=name_pk[1])
        #         print(f'updating {variable.label}')
        #         variable.mrt_prixmarche_name = name_pk[0]
        #         variable.save()
        #     else:
        #         print(f'creating {name_pk[0]}')
        #         Variable(
        #             label=f"Prix de {name_pk[0].lower()}",
        #             unit='LCY / kg',
        #             samramodel_id=1,
        #             mrt_prixmarche_name=name_pk[0],
        #             sd_type='Input',
        #         ).save()



