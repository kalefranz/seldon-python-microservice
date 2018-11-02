import flatbuffers

from .fbs import (
    SeldonMessage, Data, DefaultData, Tensor, SeldonRPC, SeldonPayload, Status, StatusValue,
    SeldonProtocolVersion, SeldonMethod,
)
from .seldon_flatbuffers import FlatbuffersInvalidMessage


def NumpyArrayToSeldonRPC(arr, names):
    builder = flatbuffers.Builder(32768)
    if len(names) > 0:
        str_offsets = []
        for i in range(len(names)):
            str_offsets.append(builder.CreateString(names[i]))
        DefaultData.DefaultDataStartNamesVector(builder, len(str_offsets))
        for i in reversed(range(len(str_offsets))):
            builder.PrependUOffsetTRelative(str_offsets[i])
        namesOffset = builder.EndVector(len(str_offsets))
    Tensor.TensorStartShapeVector(builder, len(arr.shape))
    for i in reversed(range(len(arr.shape))):
        builder.PrependInt32(arr.shape[i])
    sOffset = builder.EndVector(len(arr.shape))
    arr = arr.flatten()
    Tensor.TensorStartValuesVector(builder, len(arr))
    for i in reversed(range(len(arr))):
        builder.PrependFloat64(arr[i])
    vOffset = builder.EndVector(len(arr))
    Tensor.TensorStart(builder)
    Tensor.TensorAddShape(builder, sOffset)
    Tensor.TensorAddValues(builder, vOffset)
    tensor = Tensor.TensorEnd(builder)

    DefaultData.DefaultDataStart(builder)
    DefaultData.DefaultDataAddTensor(builder, tensor)
    DefaultData.DefaultDataAddNames(builder, namesOffset)
    defData = DefaultData.DefaultDataEnd(builder)

    Status.StatusStart(builder)
    Status.StatusAddCode(builder, 200)
    Status.StatusAddStatus(builder, StatusValue.StatusValue.SUCCESS)
    status = Status.StatusEnd(builder)

    SeldonMessage.SeldonMessageStart(builder)
    SeldonMessage.SeldonMessageAddProtocol(builder,
                                               SeldonProtocolVersion.SeldonProtocolVersion.V1)
    SeldonMessage.SeldonMessageAddStatus(builder, status)
    SeldonMessage.SeldonMessageAddDataType(builder, Data.Data.DefaultData)
    SeldonMessage.SeldonMessageAddData(builder, defData)
    seldonMessage = SeldonMessage.SeldonMessageEnd(builder)

    SeldonRPC.SeldonRPCStart(builder)
    SeldonRPC.SeldonRPCAddMethod(builder, SeldonMethod.SeldonMethod.PREDICT)
    SeldonRPC.SeldonRPCAddMessageType(builder, SeldonPayload.SeldonPayload.SeldonMessage)
    SeldonRPC.SeldonRPCAddMessage(builder, seldonMessage)
    seldonRPC = SeldonRPC.SeldonRPCEnd(builder)

    builder.FinishSizePrefixed(seldonRPC)
    return builder.Output()


def SeldonRPCToNumpyArray(data):
    seldon_msg = SeldonMessage.SeldonMessage.GetRootAsSeldonMessage(data, 0)
    if seldon_msg.Protocol() == SeldonProtocolVersion.SeldonProtocolVersion.V1:
        if seldon_msg.DataType() == Data.Data.DefaultData:
            defData = DefaultData.DefaultData()
            defData.Init(seldon_msg.Data().Bytes, seldon_msg.Data().Pos)
            names = []
            for i in range(defData.NamesLength()):
                names.append(defData.Names(i))
            tensor = defData.Tensor()
            shape = []
            for i in range(tensor.ShapeLength()):
                shape.append(tensor.Shape(i))
            values = tensor.ValuesAsNumpy()
            values = values.reshape(shape)
            return (values, names)
        else:
            raise FlatbuffersInvalidMessage("Message is not of type DefaultData")
    else:
        raise FlatbuffersInvalidMessage(
            "Message does not have correct protocol: " + str(seldon_msg.Protocol()))


