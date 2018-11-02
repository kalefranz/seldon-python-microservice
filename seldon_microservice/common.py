# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
import json

from google.protobuf.struct_pb2 import ListValue

from flask import Flask, Blueprint, request
import numpy as np

from .proto import prediction_pb2


class SeldonMicroserviceException(Exception):
    status_code = 400

    def __init__(self, message, status_code= None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = {"status":{"status":1,"info":self.message,"code":-1,"reason":"MICROSERVICE_BAD_DATA"}}
        return rv


def sanity_check_request(req):
    if not type(req) == dict:
        raise SeldonMicroserviceException("Request must be a dictionary")
    data = req.get("data")
    if data is None:
        raise SeldonMicroserviceException("Request must contain Default Data")
    if not type(data) == dict:
        raise SeldonMicroserviceException("Data must be a dictionary")
    if data.get('ndarray') is None and data.get('tensor') is None:
        raise SeldonMicroserviceException("Data dictionary has no 'ndarray' or 'tensor' keyword.")
    # TODO: Should we check more things? Like shape not being None or empty for a tensor?


def extract_message():
    jStr = request.form.get("json")
    if jStr:
        message = json.loads(jStr)
    else:
        jStr = request.args.get('json')
        if jStr:
            message = json.loads(jStr)
        else:
            raise SeldonMicroserviceException("Empty json parameter in data")
    if message is None:
        raise SeldonMicroserviceException("Invalid Data Format")
    return message


def array_to_list_value(array,lv=None):
    if lv is None:
        lv = ListValue()
    if len(array.shape) == 1:
        lv.extend(array)
    else:
        for sub_array in array:
            sub_lv = lv.add_list()
            array_to_list_value(sub_array,sub_lv)
    return lv


def rest_datadef_to_array(datadef):
    if datadef.get("tensor") is not None:
        features = np.array(datadef.get("tensor").get("values")).reshape(datadef.get("tensor").get("shape"))
    elif datadef.get("ndarray") is not None:
        features = np.array(datadef.get("ndarray"))
    else:
        features = np.array([])
    return features


def array_to_rest_datadef(array,names,original_datadef):
    datadef = {"names":names}
    if original_datadef.get("tensor") is not None:
        datadef["tensor"] = {
            "shape":array.shape,
            "values":array.ravel().tolist()
        }
    elif original_datadef.get("ndarray") is not None:
        datadef["ndarray"] = array.tolist()
    else:
        datadef["ndarray"] = array.tolist()
    return datadef


def grpc_datadef_to_array(datadef):
    data_type = datadef.WhichOneof("data_oneof")
    if data_type == "tensor":
        features = np.array(datadef.tensor.values).reshape(datadef.tensor.shape)
    elif data_type == "ndarray":
        features = np.array(datadef.ndarray)
    else:
        features = np.array([])
    return features


def array_to_grpc_datadef(array,names,data_type):
    if data_type == "tensor":
        datadef = prediction_pb2.DefaultData(
            names = names,
            tensor = prediction_pb2.Tensor(
                shape = array.shape,
                values = array.ravel().tolist()
            )
        )
    elif data_type == "ndarray":
        datadef = prediction_pb2.DefaultData(
            names = names,
            ndarray = array_to_list_value(array)
        )
    else:
        datadef = prediction_pb2.DefaultData(
            names = names,
            ndarray = array_to_list_value(array)
        )

    return datadef
