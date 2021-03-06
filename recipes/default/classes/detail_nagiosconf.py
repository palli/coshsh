from monitoring_detail import MonitoringDetail

def __detail_ident__(params={}):
    if params["monitoring_type"] == "NAGIOSCONF":
        return MonitoringDetailNagiosConf


class MonitoringDetailNagiosConf(MonitoringDetail):
    property = "generic"
    property_type = str

    def __init__(self, params):
        self.monitoring_type = params["monitoring_type"]
        # modify an attribute of service "name"
        self.name = params.get("monitoring_0", None)
        self.attribute = params.get("monitoring_1", None)
        if self.attribute.endswith('groups'):
            self.value = [params.get("monitoring_2", None)]
        else:
            self.value = params.get("monitoring_2", None)


