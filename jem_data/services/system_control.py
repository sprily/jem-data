import multiprocessing

import pymongo

import jem_data.core.domain as domain
import jem_data.core.mongo_sink as mongo_sink
import jem_data.core.table_reader as table_reader
import jem_data.core.table_request_manager as table_request_manager

mongo_config=mongo_sink.MongoConfig(
        host='127.0.0.1',
        port=27017,
        database='jem-data')

class SystemControlService(object):
    """
    The service level api.
    
    Use an instance of this class to control the system's behaviour.
    """

    def __init__(self):
        self._table_request_manager = None

    def setup(self):
        self._table_request_manager =  _setup_system()

    def resume(self):
        self._table_request_manager.resume_requests()

    def stop(self):
        self._table_request_manager.stop_requests()

    def attached_gateways(self):
        '''Returns the list of `Device`s that the system is currently
        configured with
        '''
        return []

def _setup_system():

    request_queue = multiprocessing.Queue()
    results_queue = multiprocessing.Queue()

    gateway_info = domain.Gateway(
            host="127.0.0.1",
            port=5020)

    table_reader.start_readers(gateway_info, request_queue, results_queue)

    qs = {
            gateway_info: request_queue
    }

    config = {}
    for table in xrange(1,3):
        for unit in [0x01]:
        #for unit in [0x01, 0x02]:
            device = domain.Device(gateway_info, unit)
            config[(device, table)] = 0.5

    manager = table_request_manager.start_manager(qs, config)

    _setup_mongo_collections()

    mongo_writer = multiprocessing.Process(
            target=mongo_sink.mongo_writer,
            args=(results_queue, ['archive', 'realtime'], mongo_config))

    mongo_writer.start()

    return manager
    
def _setup_mongo_collections():
    connection = pymongo.MongoClient(mongo_config.host, mongo_config.port)
    db = connection[mongo_config.database]

    if 'archive' not in db.collection_names():
        db.create_collection('archive')

    if 'realtime' not in db.collection_names():
        db.create_collection('realtime', size=1024*1024*100, capped=True, max=100)
