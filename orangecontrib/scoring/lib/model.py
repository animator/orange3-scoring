import json
from orangecontrib.scoring.lib.utils import getPFAField

class ScoringModel(object):
    def __init__(self, model, type):
        self.model = model
        self.type = type
        self.inputFields = None
        self.targetFields = None
        self.outputFields = None
        self.method = None
        self.pfaInputIsRecord = False
        self.pfaOutputIsRecord = False

        if type == "PMML":
            self.inputFields = [(f.name, f.dataType) for f in model.inputFields]
            self.outputFields = [(f.name, f.dataType) for f in model.outputFields]
            self.targetFields = [(f.name, f.dataType) for f in model.targetFields]

        if type == "PFA":
            if (model.config.method).lower() != 'map':
                raise NotImplementedError("Only 'map' method for PFA is supported. {0} is not currently supported.".format(model.config.method)) 
            self.method = model.config.method
            pfaInput = json.loads(model.config.input.toJson())
            pfaOutput = json.loads(model.config.output.toJson())
            self.inputFields, self.pfaInputIsRecord = getPFAField(pfaInput, "input")
            self.outputFields, self.pfaOutputIsRecord = getPFAField(pfaOutput, "output")

    @classmethod
    def fromPMML(cls, pmmlDoc):
        from pypmml import Model
        model = Model.fromString(pmmlDoc)
        return cls(model, "PMML")

    @classmethod
    def fromPFA(cls, pfaDoc, ext):
        from titus.genpy import PFAEngine
        if ext in (".yml", ".yaml"):
            engine = PFAEngine.fromYaml(pfaDoc)[0]
        else:
            engine = PFAEngine.fromJson(pfaDoc)[0]
        return cls(engine, "PFA")

    def predict(self, data):
        if self.type == "PFA":
            return self.model.action(data)
        if self.type == "PMML":
            return self.model.predict(data)
        raise RuntimeError("Attribute type of ScoringModel class can be PFA or PMML.")
