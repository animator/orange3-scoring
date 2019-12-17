import numpy as np

from AnyQt.QtWidgets import QGridLayout, QSizePolicy as Policy
from AnyQt.QtCore import QSize

from Orange.widgets.widget import OWWidget, Msg, Output
from Orange.data import Table, DiscreteVariable, Domain, ContinuousVariable
from Orange.widgets import gui
from Orange.evaluation import Results

from orangecontrib.scoring.lib.model import ScoringModel
from orangecontrib.scoring.lib.utils import prettifyText

class OWEvaluate(OWWidget):
    # Each widget has a name description and a set of input/outputs (referred to as the widget’s meta description).
    # Widget's name as displayed in the canvas
    name = "Evaluate PMML/PFA Model"
    # Orange Canvas looks for widgets using an orange.widgets entry point.
    id = "orange.widgets.scoring.evaluate"
    # Short widget description
    description = "Evaluate PFA (*.json, *.yaml), PMML (*.xml) or ONNX (*.onnx) model"
    # An icon resource file path for this widget
    # (a path relative to the module where this widget is defined)    
    icon = "icons/evaluate.svg"
    # Each Orange widget belongs to a category and has an associated priority within that category. 
    priority = 2
    category = "Scoring"
    keywords = ["scoring", "inference", "load", "pfa", "pmml", "onnx"]
    
    # Widget's inputs; here, a single input named "Number", of type int
    inputs = [("Data", Table, "set_data"),
              ("Scoring Model", ScoringModel, "set_model")]

    # Widget's outputs; here, a single output named "Number", of type int
    class Outputs:
        predictions = Output("Predictions", Table, doc="Scored results")  
        evaluations_results = Output("Evaluation Results", Results)              
    
    # Basic (convenience) GUI definition:
    #   a simple 'single column' GUI layout
    # want_main_area = False
    #   with a fixed or resizable geometry.
    resizing_enabled = True

    class Error(OWWidget.Error):
        connection = Msg("{}")

    def __init__(self):
        super().__init__()
        self.data = None
        self.model = None
        self.output_data = None
        self.eval_results = None
        self.inputDataAsArray = None
        self.inputWithoutFieldName = None
		# ensure the widget has some decent minimum width.        
        self.controlArea.hide()
        box = gui.vBox(self.mainArea, "Info")
        self.infolabel = gui.widgetLabel(box, 'No model or data loaded.')
        self.warnings = gui.widgetLabel(box, '')

        box = gui.hBox(self.mainArea)
        gui.rubber(box)
        self.apply_button = gui.button(
            box, self, "Score", callback=self.score)
        self.apply_button.setEnabled(False)
        self.progressBarInit()

    @staticmethod
    def sizeHint():
        return QSize(320, 100)

    def connect(self):
        return True

    def handleNewSignals(self):
        self.progressBarSet(0)
        self.output_data = None
        self.eval_results = None
        self.send_data()
        self.Error.clear()
        if self.data is not None and self.model is not None:
            conforms, fieldNamesChecked, inputFieldsChecked = self.describeFields()
            if conforms:
                self.inputDataAsArray = not inputFieldsChecked
                self.inputWithoutFieldName = not fieldNamesChecked
                self.apply_button.setEnabled(True)

    def describeFields(self):
        TAB = '&nbsp;&nbsp;&nbsp;&nbsp;'
        BR = '<br/>'
        SP = '&nbsp;'
        doFieldNameCheck = True
        doInputFieldsCheck = True
        X = self.data.X
        inputColumnNames = [field.name for field in self.data.domain.attributes]
        self.infolabel.setText('')
        text = "Input Data:"
        text += BR + "Rows - " + str(len(X))
        text += BR + "<br/>".join(prettifyText(inputColumnNames, pre="Column Names - "))
        text += BR
        text += BR + "{0} Model: ".format(self.model.type) 
        inputFields = [name for name, _ in self.model.inputFields]
        inputDataTypes = [type for _, type in self.model.inputFields]
        text += BR + "<br/>".join(prettifyText(inputFields, pre="Model Field Names - "))
        text += BR
        text += BR + 'Processing INFO:'
        if self.model.type == "PFA":
            if len(inputFields) == 1:
                if  inputFields[0] == "input_value":
                    doFieldNameCheck = False
                    text += BR + '- PFA input is of primitive Avrotype with no column name. Skipping field names check.'
                if  "array" in inputDataTypes[0]:
                    doInputFieldsCheck = False
                    text += BR + '- PFA input is of array Avrotype so value of all fields of the input data will' +\
                            BR + SP + SP + 'be converted into an array. Skipping field name and number of input fields check.'
        if doInputFieldsCheck:
            if len(inputFields) != len(inputColumnNames):
                text += BR + 'Error: No. of columns in Data is not equal to the no. of input fields of the model.'
                self.infolabel.setText(text)
                return False, doFieldNameCheck, doInputFieldsCheck
            text += BR + '- No. of columns in Data is equal to the no. of input fields of the model.'
            if doFieldNameCheck:
                if sorted(inputFields) != sorted(inputColumnNames):
                    text += BR + 'Error: Column names in Data do not match the input field names of the model.'
                    self.infolabel.setText(text)
                    return False, doFieldNameCheck, doInputFieldsCheck
                text += BR + '- Column names in Data match with the input field names of the model.'        
        self.infolabel.setText(text)
        return True, doFieldNameCheck, doInputFieldsCheck

    def send_data(self):
        self.Outputs.predictions.send(self.output_data)
        self.Outputs.evaluations_results.send(self.eval_results)
        self.apply_button.setEnabled(False)  

    def set_data(self, data):
        self.data = data
        self.handleNewSignals()

    def set_model(self, model):
        self.model = model
        self.handleNewSignals()

    def score(self):
        self.output_data = None  
        self.progressBarSet(0)
        #cv = ["null", "boolean", "integer", "int", "long", "float", "double"]
        dv = ["string", "bytes"]
        res = []
        inputColumnNames = [field.name for field in self.data.domain.attributes]
        dvFieldSet = {name: [] for name, type in self.model.outputFields if type in dv}
        nRows = len(self.data.X)
        for cnt, row in enumerate(self.data.X):
            self.progressBarSet(int(100*cnt/nRows) -10)
            datum = None
            if self.inputWithoutFieldName:
                datum = row[0]
            elif self.inputDataAsArray:
                datum = {self.model.inputFields[0][0]: list(row)}
            else:
                datum = dict(zip(inputColumnNames, row))
            if datum is not None:
                result = self.model.predict(datum)
                if "output_value" == self.model.outputFields[0][0]:
                    if "output_value" in dvFieldSet.keys():
                        if result in dvFieldSet["output_value"]:
                            result = dvFieldSet["output_value"].index(result)
                        else:
                            dvFieldSet["output_value"].append(result)
                            result = len(dvFieldSet["output_value"]) - 1
                    res.append([result, ])
                else:
                    resRow = []
                    for name, _ in self.model.outputFields:
                        if name in dvFieldSet.keys():
                            if result[name] in dvFieldSet[name]:
                                resRow.append(dvFieldSet[name].index(result[name]))
                            else:
                                dvFieldSet[name].append(result[name])
                                resRow.append(len(dvFieldSet[name])-1)
                        else:
                            resRow.append(result[name])  
                    res.append(resRow)                          
            else:
                raise RuntimeError("Error detecting input data row - {0}".format(row))
        DomainX = self.data.domain.attributes
        DomainY = [DiscreteVariable(name, values=dvFieldSet[name]) if name in dvFieldSet.keys() else ContinuousVariable(name) \
                    for name, _ in self.model.outputFields]
        DomainM = self.data.domain.class_vars
        output_data_domain = Domain(DomainX, class_vars=DomainY, metas=DomainM)     
        self.output_data = Table.from_numpy(output_data_domain, self.data.X, Y=np.array(res), metas=self.data._Y)   
        self.output_data.name = "Result Table"
        if len(DomainM) > 0 and len(res[0])==1:
            self.eval_result_matrix(np.array(res), DomainY)
        self.send_data()
        self.progressBarSet(100)

    def eval_result_matrix(self, predicted_results, domain_results):
        self.eval_results = Results(self.data,
                                    nrows=len(self.data),
                                    row_indices = np.arange(len(self.data)),                       
                                    actual=self.data.Y,
                                    predicted=np.array([predicted_results.ravel()]))


if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview  # since Orange 3.20.0
    from orangecontrib.scoring.lib.readers import PFAFormat
    import os
    pfaFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../tests/sample_iris.json")
    WidgetPreview(OWEvaluate).run(set_data=Table("iris"),
                                  set_model=PFAFormat.get_reader(pfaFile).read())

