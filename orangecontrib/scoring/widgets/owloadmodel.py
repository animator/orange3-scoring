import os
import logging
import json
from warnings import catch_warnings
from typing import List

from AnyQt.QtWidgets import QStyle, QGridLayout, QSizePolicy as Policy
from AnyQt.QtCore import Qt, QTimer, QSize

from Orange.data.io import class_from_qualified_name
from Orange.widgets import widget, gui
from Orange.widgets.settings import Setting, ContextSetting, \
    PerfectDomainContextHandler, SettingProvider
from Orange.widgets.utils.filedialogs import RecentPathsWComboMixin, \
    open_filename_dialog
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.widget import Output

# Backward compatibility: class RecentPath used to be defined in this module,
# and it is used in saved (pickled) settings. It must be imported into the
# module's namespace so that old saved settings still work
from Orange.widgets.utils.filedialogs import RecentPath

log = logging.getLogger(__name__)
RAISE_ISSUE = """\nPlease raise an issue 
here - https://github.com/animator/orange3-scoring/issues
in case you need further help."""

def resolveUnion(pfaUnion):
    validAvroTypes = ["null", "boolean", "int", "long", "float", "double", "string", "bytes"]
    for item in pfaUnion:
        if isinstance(item, str):
            if item in validAvroTypes:
                continue
            else:
                raise NotImplementedError("Un-identified AvroType {0}".format(item))
        if isinstance(item, dict):
            raise NotImplementedError("record, map, array, enum are not supported in union {0}{1}".format(pfaUnion, RAISE_ISSUE))
    return pfaUnion

def getPFAField(pfaArg, argType):       
    # If input/output is of single AvroType
    validAvroTypes = ["null", "boolean", "int", "long", "float", "double", "string", "bytes"]
    if isinstance(pfaArg, str):
        if pfaArg in validAvroTypes:
            return [(argType+"_value", pfaArg)], False
        else:
            raise NotImplementedError("Un-identified {0} AvroType {1}".format(argType, pfaArg))

    # Handling unions
    # Note: no complex type: map, array, enum, record, etc. allowed in a union
    if isinstance(pfaArg, list):
        if all(isinstance(t, str) for t in pfaArg):
            if set(pfaArg).issubset(validAvroTypes):
                return [(argType+"_value", ",".join(pfaArg))], False
            else:
                raise NotImplementedError("Un-identified AvroType in the tagged union {0} {1}{2}".format(argType, 
                                                                                                         pfaArg, 
                                                                                                         RAISE_ISSUE))
        else:
            raise NotImplementedError("""{0} of AvroType 'union' should not contain any 
        complex AvroType (map, array, enum, record, etc.){1}""".format(argType, RAISE_ISSUE))

    # Process input fields
    if isinstance(pfaArg, dict):
        if pfaArg["type"] in ('record', 'array', 'enum', 'map'):
            if pfaArg["type"] == "map":
                raise NotImplementedError("""Unable to determine the field names for AvroType 'map' {0}. 
            Try converting the 'map' into a 'record' AvroType.{1}""".format(argType, RAISE_ISSUE))
            elif pfaArg["type"] == "array":
                if "items" in pfaArg.keys():
                    if isinstance(pfaArg["items"], str) and pfaArg["items"] in validAvroTypes:
                        return [(argType+"_value", pfaArg["type"]+" of "+pfaArg["items"])], False
                    if isinstance(pfaArg["items"], list):
                        itemTypes = resolveUnion(pfaArg["items"])
                        return [(argType+"_value", pfaArg["type"]+" of "+ ",".join(itemTypes))], False
                raise NotImplementedError("Unable to determine the AvroType of items in {0} 'array' {1}.{2}".format(argType, 
                                                                                                                    pfaArg, 
                                                                                                                    RAISE_ISSUE))
            elif pfaArg["type"] == "enum":
                return [(argType+"_value", pfaArg["type"])], False
            else:
                if "fields" not in pfaArg.keys():
                    raise NotImplementedError("AvroType 'record' {0} with no fields.{1}".format(argType, RAISE_ISSUE)) 
                fields = []
                for f in pfaArg["fields"]:
                    if isinstance(f["type"], list):
                        fields.append((f["name"], ",".join(resolveUnion(f["type"]))))
                    elif isinstance(f["type"], str) and f["type"] in validAvroTypes:
                        fields.append((f["name"], f["type"]))
                    elif isinstance(f["type"], dict):
                        if f["type"]["type"] in ("enum", "array"):
                            fields.append((f["name"], f["type"]["type"]))
                        else:
                            raise NotImplementedError("Field {0} of AvroType {1} is not supported{2}".format(f["name"], 
                                                                                                             f["type"], 
                                                                                                             RAISE_ISSUE))
                    else:
                        raise NotImplementedError("Field {0} of AvroType {1} is not supported.{2}".format(f["name"], 
                                                                                                          f["type"], 
                                                                                                          RAISE_ISSUE))
                if "array" in [t for _, t in fields] and len(fields)>1:
                    raise NotImplementedError("""Field with datatype 'array' is not supported in the 
                presence of other fields {0}{1}""".format(fields, RAISE_ISSUE))
                return fields, True
        else:
            raise NotImplementedError("""'record', 'enum' and 'array' datatype for {0} is supported. 
        {1} is not currently supported.{2}""".format(argType, pfaArg["type"], RAISE_ISSUE)) 
    
    raise TypeError("Un-identified {0} of datatype {1}. Valid types - list, str, dict{2}".format(argType, 
                                                                                                 type(pfaArg), 
                                                                                                 RAISE_ISSUE))

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

class PMMLFormat(object):
    PRIORITY = 1
    DESCRIPTION = "PMML file"
    EXTENSIONS = (".xml", ".xsd", ".pmml")
    
    def __init__(self, filename):
        self.filename = filename

    @classmethod
    def get_reader(cls, filename):
        try:
            return PMMLReader(filename)
        except:
            raise IOError('No readers for file "{}"'.format(filename))

    @classmethod
    def qualified_name(cls):
        return cls.__module__ + '.' + cls.__name__

class PFAFormat(object):
    PRIORITY = 2
    DESCRIPTION = "PFA file"
    EXTENSIONS = (".pfa", ".json", ".yml", ".yaml")
    
    def __init__(self, filename):
        self.filename = filename

    @classmethod
    def get_reader(cls, filename):
        try:
            return PFAReader(filename)
        except:
            raise IOError('No readers for file "{}"'.format(filename))

    @classmethod
    def qualified_name(cls):
        return cls.__module__ + '.' + cls.__name__

class PMMLReader(object):
    """Reader for PMML files"""
    def __init__(self, filename):
        self.filename = filename

    def read(self):
        pmml = open(self.filename, 'r').read()      
        return ScoringModel.fromPMML(pmml)

class PFAReader(object):
    """Reader for PFA files"""
    def __init__(self, filename):
        self.filename = filename

    def read(self):
        pfa = open(self.filename, 'r').read()
        _, ext = os.path.splitext(self.filename)
        return ScoringModel.fromPFA(pfa, ext)

class OWLoadModel(widget.OWWidget, RecentPathsWComboMixin):
    name = "Load PMML/PFA Model"
    id = "orange.widgets.scoring.model"
    description = "Load model from an input PMML file ( *.pmml, *.xml) " \
                  "or from an input PFA file ( *.pfa, *.json, *.yml, *.yaml) " \
                  "and send the model to the output."
    icon = "icons/model.svg"
    priority = 1
    category = "Scoring"
    keywords = ["pmml", "pfa", "load", "read", "open"]

    class Outputs:
        data = Output("Scoring Model", ScoringModel,
                      doc="PMML/PFA Model read from the input file.")

    want_main_area = False

    SEARCH_PATHS = [("location", os.getcwd())]
    SIZE_LIMIT = 1e7
    LOCAL_FILE, URL = range(2)

    settingsHandler = PerfectDomainContextHandler(
        match_values=PerfectDomainContextHandler.MATCH_VALUES_ALL
    )

    # pylint seems to want declarations separated from definitions
    recent_paths: List[RecentPath]

    # Overload RecentPathsWidgetMixin.recent_paths to set defaults
    recent_paths = Setting([])
    source = Setting(LOCAL_FILE)   

    class Warning(widget.OWWidget.Warning):
        file_too_big = widget.Msg("The file is too large to load automatically."
                                  " Press Reload to load.")
        load_warning = widget.Msg("Read warning:\n{}")

    class Error(widget.OWWidget.Error):
        file_not_found = widget.Msg("File not found.")
        missing_reader = widget.Msg("Missing reader.")
        unknown = widget.Msg("Read error:\n{}")

    class NoFileSelected:
        pass

    def __init__(self):
        super().__init__()
        RecentPathsWComboMixin.__init__(self)
        self.domain = None
        self.data = None
        self.loaded_file = ""
        self.reader = None

        layout = QGridLayout()
        gui.widgetBox(self.controlArea, margin=0, orientation=layout)
        vbox = gui.radioButtons(None, self, "source", box=True, addSpace=True,
                                callback=self.load_data, addToLayout=False)

        rb_button = gui.appendRadioButton(vbox, "File:", addToLayout=False)
        layout.addWidget(rb_button, 0, 0, Qt.AlignVCenter)

        box = gui.hBox(None, addToLayout=False, margin=0)
        box.setSizePolicy(Policy.MinimumExpanding, Policy.Fixed)
        self.file_combo.setSizePolicy(Policy.MinimumExpanding, Policy.Fixed)
        self.file_combo.activated[int].connect(self.select_file)
        box.layout().addWidget(self.file_combo)
        layout.addWidget(box, 0, 1)

        file_button = gui.button(
            None, self, '...', callback=self.browse_file, autoDefault=False)
        file_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        file_button.setSizePolicy(Policy.Maximum, Policy.Fixed)
        layout.addWidget(file_button, 0, 2)

        reload_button = gui.button(
            None, self, "Reload", callback=self.load_data, autoDefault=False)
        reload_button.setIcon(self.style().standardIcon(
            QStyle.SP_BrowserReload))
        reload_button.setSizePolicy(Policy.Fixed, Policy.Fixed)
        layout.addWidget(reload_button, 0, 3)

        box = gui.vBox(self.controlArea, "Info")
        self.infolabel = gui.widgetLabel(box, 'No model loaded.')
        self.warnings = gui.widgetLabel(box, '')
        
        box = gui.hBox(self.controlArea)
        gui.rubber(box)

        self.apply_button = gui.button(
            box, self, "Send", callback=self.send_data)
        self.apply_button.setEnabled(False)
        self.apply_button.setFixedWidth(170)

        self.set_file_list()
        # Must not call open_file from within __init__. open_file
        # explicitly re-enters the event loop (by a progress bar)

        self.setAcceptDrops(True)

        if self.source == self.LOCAL_FILE:
            last_path = self.last_path()
            if last_path and os.path.exists(last_path) and \
                    os.path.getsize(last_path) > self.SIZE_LIMIT:
                self.Warning.file_too_big()
                return

        QTimer.singleShot(0, self.load_data)

    @staticmethod
    def sizeHint():
        return QSize(600, 30)

    def select_file(self, n):
        assert n < len(self.recent_paths)
        super().select_file(n)
        if self.recent_paths:
            self.source = self.LOCAL_FILE
            self.load_data()
            self.set_file_list()

    def browse_file(self):
        start_file = self.last_path() or os.path.expanduser("~/")

        readers = [PMMLFormat, PFAFormat, ]
        filename, file_format, filter = open_filename_dialog(start_file, None, readers)
        if not filename:
            return
        self.add_path(filename)
        if file_format is not None:
            self.recent_paths[0].file_format = file_format.qualified_name()

        self.source = self.LOCAL_FILE
        self.load_data()

    # Open a file, create data from it and send it over the data channel
    def load_data(self):
        # We need to catch any exception type since anything can happen in
        # file readers
        self.closeContext()
        self.apply_button.setEnabled(False)
        self.clear_messages()
        self.set_file_list()

        error = self._try_load()
        if error:
            error()
            self.data = None
            self.Outputs.data.send(None)
            self.infolabel.setText("No model.")

    def _try_load(self):
        # pylint: disable=broad-except
        if self.last_path() and not os.path.exists(self.last_path()):
            return self.Error.file_not_found
        try:
            self.reader = self._get_reader()
            assert self.reader is not None
        except Exception:
            return self.Error.missing_reader

        if self.reader is self.NoFileSelected:
            self.Outputs.data.send(None)
            return None

        with catch_warnings(record=True) as warnings:
            try:
                model = self.reader.read()
            except Exception as ex:
                log.exception(ex)
                return lambda x=ex: self.Error.unknown(str(x))
            if warnings:
                self.Warning.load_warning(warnings[-1].message.args[0])

        self.infolabel.setText(self._describe(model))

        self.loaded_file = self.last_path()
        self.data = model
        self.apply_button.setEnabled(True)
        return None

    def _get_reader(self):
        if self.source == self.LOCAL_FILE:
            path = self.last_path()
            if path is None:
                return self.NoFileSelected
            if self.recent_paths and self.recent_paths[0].file_format:
                qname = self.recent_paths[0].file_format
                reader_class = class_from_qualified_name(qname)
                reader = reader_class.get_reader(path)
            else:
                _, ext = os.path.splitext(path)
                reader = self.NoFileSelected
                if ext in PMMLFormat.EXTENSIONS:
                    reader = PMMLFormat.get_reader(path)
                if ext in PFAFormat.EXTENSIONS:
                    reader = PFAFormat.get_reader(path)
            return reader
        return self.NoFileSelected

    @staticmethod
    def _describe(modelFormat):
        text = ""
        if modelFormat.type == "PFA":   
            text += "Method:<br/>&nbsp;&nbsp;&nbsp;&nbsp;" + modelFormat.method + "<br/>"

        text += "Input fields(s)"
        if len(modelFormat.inputFields) > 0:
            text += ":<br/>&nbsp;&nbsp;&nbsp;&nbsp;" + \
                ", ".join([name+ " ("+dataType+")" for name, dataType in modelFormat.inputFields])
        else:
            text += ":<br/>&nbsp;&nbsp;&nbsp;&nbsp;None"
        text += "<br/>Output fields(s)"
        if len(modelFormat.outputFields) > 0:
            text += ":<br/>&nbsp;&nbsp;&nbsp;&nbsp;" + \
                ", ".join([name+ " ("+dataType+")" for name, dataType in modelFormat.outputFields])  
        else:
            text += ":<br/>&nbsp;&nbsp;&nbsp;&nbsp;None"                      
    
        if modelFormat.type == "PMML":
            text += "<br/>Target fields(s)"
            if len(modelFormat.targetFields) > 0:
                text += ":<br/>&nbsp;&nbsp;&nbsp;&nbsp;" + \
                    ", ".join([name+ " ("+dataType+")" for name, dataType in modelFormat.targetFields]) 
            else:
                text += ":<br/>&nbsp;&nbsp;&nbsp;&nbsp;None"                               
        return text

    def get_widget_name_extension(self):
        _, name = os.path.split(self.loaded_file)
        return os.path.splitext(name)[0]

    def send_data(self):
        self.Outputs.data.send(self.data)
        self.apply_button.setEnabled(False)    

if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWLoadModel).run()
