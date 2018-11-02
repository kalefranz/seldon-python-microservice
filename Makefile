build_docker_image:
	./build_image.sh

push_to_registry:
	./push_image.sh

build_proto:
	cp ../../proto/prediction.proto proto
	python -m grpc.tools.protoc -I./ --python_out=./ --grpc_python_out=./ ./proto/prediction.proto

seldon.json:
	cp ../../openapi/wrapper.oas3.json seldon.json

clean:
	rm -f proto/prediction.proto
	rm -f proto/prediction_pb2_grpc.py
	rm -f proto/prediction_pb2.py


.PHONY: devenv
devenv:
	conda $(shell [ -d ./devenv ] && echo install || echo create) -y -p ./devenv \
		python \
		pip \
		grpcio \
		protobuf \
		flask \
		flask-cors \
		redis-py \
		tornado \
		requests \
		numpy
	./devenv/bin/pip install flatbuffers
	./devenv/bin/pip install -e .

#		flatbuffers>=1.10 \
#       python-flatbuffers


fbs:
	/usr/local/bin/flatc --python -o seldon_microservice/fbs seldon_microservice/fbs/prediction.fbs


proto:
	/usr/local/bin/python3 -m grpc.tools.protoc \
		-I seldon_microservice/proto \
		--python_out seldon_microservice/proto \
		--grpc_python_out=seldon_microservice/proto \
		seldon_microservice/proto/prediction.proto


