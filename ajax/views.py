from django.http import HttpResponse
from django.utils import simplejson as json
from django.utils.translation import ugettext as _
from django.utils.importlib import import_module
from django.core.serializers.json import DjangoJSONEncoder
from decorator import decorator
from ajax.exceptions import AJAXError, NotRegistered
import ajax


@decorator
def json_response(f, *args, **kwargs):
    """Wrap a view in JSON.

    This decorator runs the given function and looks out for ajax.AJAXError's,
    which it encodes into a proper HttpResponse object. If an unknown error
    is thrown it's encoded as a 500.

    All errors are then packaged up with an appropriate Content-Type and a JSON
    body that you can inspect in JavaScript on the client. They look like:

    {
        "message": "Error message here.", 
        "code": 500
    }

    Please keep in mind that raw exception messages could very well be exposed
    to the client if a non-AJAXError is thrown.
    """ 
    try:
        result = f(*args, **kwargs)
    except AJAXError, e:
        result = e.get_response()
    except Exception, e:
        result = AJAXError(500, str(e)).get_response()

    result['Content-Type'] = 'application/json'
    return result


@json_response
def endpoint_loader(request, application, model, **kwargs):
    """Load an AJAX endpoint.

    This will load either an ad-hoc endpoint or it will load up a model 
    endpoint depending on what it finds. It first attempts to load ``model``
    as if it were an ad-hoc endpoint. Alternatively, it will attempt to see if
    there is a ``ModelEndpoint`` for the given ``model``.
    """
    try:
        module = import_module('%s.endpoints' % application)
    except ImportError, e:
        raise AJAXError(404, _('AJAX endpoint does not exist.'))

    if hasattr(module, model):
        # This is an ad-hoc endpoint
        endpoint = getattr(module, model)
    else:
        # This is a model endpoint
        pk = kwargs.get('pk', None)
        method = kwargs.get('method', 'create').lower()

        try:
            model_endpoint = ajax.endpoint.load(model, application, method, pk)
            if not model_endpoint.authenticate(request, application, method):
                raise AJAXError(403, _('User is not authorized.'))

            endpoint = getattr(model_endpoint, method)
        except NotRegistered:
            raise AJAXError(500, _('Invalid model.'))       

    data = endpoint(request) 
    if isinstance(data, HttpResponse):
        return data 
    else:
        return HttpResponse(json.dumps(data, indent=4, cls=DjangoJSONEncoder))
