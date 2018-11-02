# -*- coding: utf-8 -*-

# python -m grpc.tools.protoc -I./ --python_out=./ --grpc_python_out=./ ./proto/prediction.proto


# get_wrappers_and_protos:
#     mkdir -p _wrappers/python/proto
#     mkdir -p _wrappers/python/fbs
#     cp $(SELDON_CORE_DIR)/wrappers/python/*_microservice.py _wrappers/python
#     cp $(SELDON_CORE_DIR)/wrappers/python/microservice.py _wrappers/python
#     cp $(SELDON_CORE_DIR)/wrappers/python/persistence.py _wrappers/python
#     cp $(SELDON_CORE_DIR)/wrappers/python/seldon_requirements.txt _wrappers/python
#     cp $(SELDON_CORE_DIR)/wrappers/python/__init__.py _wrappers/python
#     cp $(SELDON_CORE_DIR)/proto/prediction.proto _wrappers/python/proto
#     cp $(SELDON_CORE_DIR)/wrappers/python/seldon_flatbuffers.py _wrappers/python
#     flatc --python -o _wrappers/python/fbs ../../../fbs/prediction.fbs
#     touch _wrappers/python/proto/__init__.py
#     touch _wrappers/python/fbs/__init__.py
#     cp $(SELDON_CORE_DIR)/openapi/wrapper.oas3.json _wrappers/python/seldon.json
