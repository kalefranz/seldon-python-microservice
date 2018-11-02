import argparse
import os
import importlib
import json
import time
import logging
import multiprocessing as mp

from . import __version__

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PARAMETERS_ENV_NAME = "PREDICTIVE_UNIT_PARAMETERS"
SERVICE_PORT_ENV_NAME = "PREDICTIVE_UNIT_SERVICE_PORT"
DEFAULT_PORT = 5000

DEBUG_PARAMETER = "SELDON_DEBUG"

ANNOTATIONS_FILE = "/etc/podinfo/annotations"


def startServers(target1, target2):
    p1 = mp.Process(target=target1)
    p1.deamon = True
    p1.start()

    p2 = mp.Process(target=target2)
    p2.deamon = True
    p2.start()

    p1.join()
    p2.join()


def parse_parameters(parameters):
    type_dict = {
        "INT":int,
        "FLOAT":float,
        "DOUBLE":float,
        "STRING":str,
        "BOOL":bool
    }
    parsed_parameters = {}
    for param in parameters:
        name = param.get("name")
        value = param.get("value")
        type_ = param.get("type")
        parsed_parameters[name] = type_dict[type_](value)
    return parsed_parameters


def load_annotations():
    annotations = {}
    try:
        if os.path.isfile(ANNOTATIONS_FILE):
            with open(ANNOTATIONS_FILE, "r") as ins:
                for line in ins:
                    line = line.rstrip()
                    parts = line.split("=")
                    if len(parts) == 2:
                        value = parts[1]
                        value = parts[1][1:-1]
                        logger.info("Found annotation %s:%s ",parts[0],value)
                        annotations[parts[0]] = value
                    else:
                        logger.info("bad annotation [%s]",line)
    except:
        logger.error("Failed to open annotations file %s",ANNOTATIONS_FILE)
    return annotations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument("interface_name",type=str,help="Name of the user interface.")
    parser.add_argument("api_type",type=str,choices=["REST","GRPC","FBS"])

    parser.add_argument("--service-type",type=str,choices=["MODEL","ROUTER","TRANSFORMER","COMBINER","OUTLIER_DETECTOR"],default="MODEL")
    parser.add_argument("--persistence",nargs='?',default=0,const=1,type=int)
    parser.add_argument("--parameters",type=str,default=os.environ.get(PARAMETERS_ENV_NAME,"[]"))
    args = parser.parse_args()

    parameters = parse_parameters(json.loads(args.parameters))

    DEBUG = False
    if parameters.get(DEBUG_PARAMETER):
        parameters.pop(DEBUG_PARAMETER)
        DEBUG = True

    annotations = load_annotations()
    logger.info("Annotations %s",annotations)

    interface_file = importlib.import_module(args.interface_name)
    user_class = getattr(interface_file,args.interface_name)

    if args.persistence:
        from .persistence import persist, restore
        user_object = restore(user_class,parameters,debug=DEBUG)
        persist(user_object,parameters.get("push_frequency"))
    else:
        user_object = user_class(**parameters)

    if args.service_type == "MODEL":
        from . import model_microservice as seldon_microservice
    elif args.service_type == "ROUTER":
        from . import router_microservice as seldon_microservice
    elif args.service_type == "TRANSFORMER":
        from . import transformer_microservice as seldon_microservice
    elif args.service_type == "OUTLIER_DETECTOR":
        from . import outlier_detector_microservice as seldon_microservice

    port = int(os.environ.get(SERVICE_PORT_ENV_NAME,DEFAULT_PORT))

    if args.api_type == "REST":
        def rest_prediction_server():
            print("Starting REST prediction server")
            app = seldon_microservice.get_rest_microservice(user_object,debug=DEBUG)
            app.run(host=os.environ.get("APP_HOST", "0.0.0.0"), port=port)

        server1_func=rest_prediction_server

    elif args.api_type=="GRPC":
        def grpc_prediction_server():
            server = seldon_microservice.get_grpc_server(user_object,debug=DEBUG,annotations=annotations)
            server.add_insecure_port("0.0.0.0:{}".format(port))
            server.start()

            print("GRPC Microservice Running on port {}".format(port))
            while True:
                time.sleep(1000)

        server1_func=grpc_prediction_server

    elif args.api_type=="FBS":
        def fbs_prediction_server():
            seldon_microservice.run_flatbuffers_server(user_object,port)

        server1_func=fbs_prediction_server

    else:
        server1_func = None

    if hasattr(user_object, 'custom_service') and callable(getattr(user_object, 'custom_service')):
        server2_func = user_object.custom_service
    else:
        server2_func = None

    startServers(server1_func, server2_func)


if __name__ == "__main__":
    main()
