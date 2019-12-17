import os
from orangecontrib.scoring.lib.model import ScoringModel

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
