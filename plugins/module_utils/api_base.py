from zeep import xsd, Client, Settings
from zeep.helpers import serialize_object as serialize_zeep_object
from json import dumps as json_dumps
from json import loads as json_loads
from datetime import datetime

DEBUG_LOG = True
DEBUG_LOG_FILE = '/tmp/ascio_api_request.log'


def ascio_api(method: str, user: str, password: str, request: dict, request_type: str = None) -> dict:
    # abstraction function since this basic construct is used for all ascio APIv3 calls
    wsdl = "https://aws.ascio.com/v3/aws.wsdl"
    settings = Settings(strict=False)
    client = Client(wsdl=wsdl, settings=settings)

    client.set_ns_prefix('v3', 'http://www.ascio.com/2013/02')
    header = xsd.Element(
        '{http://www.ascio.com/2013/02}SecurityHeaderDetails',
        xsd.ComplexType([
            xsd.Element(
                '{http://www.ascio.com/2013/02}Account',
                xsd.String()),
            xsd.Element(
                '{http://www.ascio.com/2013/02}Password',
                xsd.String())
        ])
    )
    header_value = header(
        Account=user,
        Password=password,
    )
    if request_type is not None:
        request_type = client.get_type(request_type)
        request = request_type(**request)

    if DEBUG_LOG:
        with open(DEBUG_LOG_FILE, 'a+', encoding='utf-8') as log:
            log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Request for method '{method}': '{request}'\n\n")

    _method = getattr(client.service, method)
    response = _method(_soapheaders=[header_value], request=request)
    response_dict = serialize_zeep_object(response, dict)
    return json_loads(json_dumps(response_dict, default=str))  # json dump/load used to get rid of unsupported data-types
