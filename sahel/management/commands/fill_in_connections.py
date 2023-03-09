from django.core.management.base import BaseCommand
from sahel.models import Variable, VariableConnection
import re


class Command(BaseCommand):
    help = 'Automatically fills in VariableConnections based on equations'

    def handle(self, *args, **options):
        variables = Variable.objects.filter(sd_type__in=[Variable.VARIABLE, Variable.FLOW], equation__isnull=False)
        connections = VariableConnection.objects.all().values()
        objs = []
        for variable in variables:
            to_pk = variable.pk
            from_pks = list(set(re.findall(r'_E(.+?)_', variable.equation)))
            existing_from_pks = [conn.get('from_variable_id') for conn in connections if conn.get('to_variable_id') == to_pk]
            for from_pk in from_pks:
                if int(from_pk) not in existing_from_pks:
                    print(f"was missing {from_pk} from {variable}")
                    objs.append(VariableConnection(
                        from_variable_id=from_pk,
                        to_variable_id=to_pk,
                    ))

        VariableConnection.objects.bulk_create(objs)

        return



