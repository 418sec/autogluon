import io, logging, pickle, boto3
import builtins

safe_builtins = {
    'range',
    'complex',
    'set',
    'frozenset',
    'slice',
}

from . import load_pointer
from .. import s3_utils

logger = logging.getLogger(__name__)

class RestrictedUnpickler(pickle.Unpickler):

    def find_class(self, module, name):
        """Only allow safe classes from builtins"""
        if module == "builtins" and name in safe_builtins:
            return getattr(builtins, name)
        """Forbid everything else"""
        raise pickle.UnpicklingError("global '%s.%s' is forbidden" %
                                     (module, name))

def restricted_loads(s):
    """Helper function analogous to pickle.loads()"""
    return RestrictedUnpickler(io.BytesIO(s)).load()

def load(path, format=None, verbose=True):
    if path.endswith('.pointer'):
        format = 'pointer'
    elif s3_utils.is_s3_url(path):
        format = 's3'
    if format == 'pointer':
        content_path = load_pointer.get_pointer_content(path)
        if content_path == path:
            raise RecursionError('content_path == path! : ' + str(path))
        return load(path=content_path)
    elif format == 's3':
        if verbose: logger.log(15, 'Loading: %s' % path)
        s3_bucket, s3_prefix = s3_utils.s3_path_to_bucket_prefix(s3_path=path)
        s3 = boto3.resource('s3')
        return pickle.loads(s3.Bucket(s3_bucket).Object(s3_prefix).get()['Body'].read())

    if verbose: logger.log(15, 'Loading: %s' % path)
    with open(path, 'rb') as fin:
        restricted_loads(fin.read())
        object = pickle.load(fin)
    return object


def load_with_fn(path, pickle_fn, format=None, verbose=True):
    if path.endswith('.pointer'):
        format = 'pointer'
    elif s3_utils.is_s3_url(path):
        format = 's3'
    if format == 'pointer':
        content_path = load_pointer.get_pointer_content(path)
        if content_path == path:
            raise RecursionError('content_path == path! : ' + str(path))
        return load_with_fn(content_path, pickle_fn)
    elif format == 's3':
        if verbose: logger.log(15, 'Loading: %s' % path)
        s3_bucket, s3_prefix = s3_utils.s3_path_to_bucket_prefix(s3_path=path)
        s3 = boto3.resource('s3')
        # Has to be wrapped in IO buffer since s3 stream does not implement seek()
        buff = io.BytesIO(s3.Bucket(s3_bucket).Object(s3_prefix).get()['Body'].read())
        return pickle_fn(buff)

    if verbose: logger.log(15, 'Loading: %s' % path)
    with open(path, 'rb') as fin:
        object = pickle_fn(fin)
    return object
