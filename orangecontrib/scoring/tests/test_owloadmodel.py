import unittest, os
from Orange.widgets.tests.base import WidgetTest

from orangecontrib.scoring.widgets.owloadmodel import getPFAField, OWLoadModel, ScoringModel, \
    PFAFormat, PMMLFormat, PFAReader, PMMLReader


class PFAFieldTests(unittest.TestCase):
    def test_asserts01(self):
        self.assertRaisesRegexp(TypeError, "Un-identified ", lambda: getPFAField(set("madeUpAvroType"), "input"))
        self.assertRaisesRegexp(TypeError, "Un-identified ", lambda: getPFAField(1, "input"))
        self.assertRaisesRegexp(TypeError, "Un-identified ", lambda: getPFAField(1.3, "input"))
        self.assertRaisesRegexp(TypeError, "Un-identified ", lambda: getPFAField(("bool", "float"), "input"))

    def test_asserts02(self):
        self.assertRaisesRegexp(NotImplementedError,
                                "Un-identified input AvroType madeUpAvroType", 
                                lambda: getPFAField("madeUpAvroType", "input"))

    def test_field1(self):
        field, type = getPFAField("boolean", "input")
        self.assertEqual(field, [("input_value", "boolean")])
        self.assertEqual(type, False)

        field, type = getPFAField("int", "input")
        self.assertEqual(field, [("input_value", "int")])
        self.assertEqual(type, False)

    def test_field2(self):
        field, type = getPFAField(["boolean", "null"], "input")
        self.assertEqual(field, [("input_value", "boolean,null")])
        self.assertEqual(type, False)

        field, type = getPFAField(["int", "long", "float", "double"], "input")
        self.assertEqual(field, [("input_value", "int,long,float,double")])
        self.assertEqual(type, False)

    def test_asserts03(self):
        self.assertRaisesRegexp(NotImplementedError, 
                                "of AvroType 'union' should not contain any",
                                lambda: getPFAField(["boolean", {"type": "array", "items": "int"}], "input"))

    def test_asserts04(self):
        self.assertRaisesRegexp(NotImplementedError, 
                                "input of AvroType 'union' should not contain",
                                lambda: getPFAField(["boolean", "madeUpAvroType", {"type": "array", "items": "int"}], "input"))

        self.assertRaisesRegexp(NotImplementedError, 
                                "tagged union",
                                lambda: getPFAField(["boolean", "madeUpAvroType"], "input"))

    def test_asserts05(self):
        self.assertRaisesRegexp(NotImplementedError, 
                                "Unable to determine the field names for AvroType 'map'",
                                lambda: getPFAField({"type": "map", "values": "int"}, "input"))

    def test_field3(self):
        field, type = getPFAField({"type": "array", "items": "int"}, "input")
        self.assertEqual(field, [("input_value", "array of int")])
        self.assertEqual(type, False)

        field, type = getPFAField({"type": "array", "items": ["int", "double", "null"]}, "input")
        self.assertEqual(field, [("input_value", "array of int,double,null")])
        self.assertEqual(type, False)

    def test_asserts06(self):
        self.assertRaisesRegexp(NotImplementedError, 
                                "record, map, array, enum are not supported in union",
                                lambda: getPFAField({"type": "array", "items": ["int", "double", {"type": "map", "values": "int"}]}, "input"))

        self.assertRaisesRegexp(NotImplementedError, 
                                "record, map, array, enum are not supported in union",
                                lambda: getPFAField({"type": "array", "items": ["int", "double", {"type": "array", "items": "int"}]}, "input"))                                

        self.assertRaisesRegexp(NotImplementedError, 
                                "Unable to determine the AvroType of items in ",
                                lambda: getPFAField({"type": "array"}, "input")) 

    def test_field4(self):
        field, type = getPFAField({"type": "enum", "name": "Test", "symbols": ["A", "B", "C"]}, "input")
        self.assertEqual(field, [("input_value", "enum")])
        self.assertEqual(type, False)

    def test_field5(self):
        field, type = getPFAField({"type": "record", "name": "Input", 
                                   "fields": [
                                       {"name": "x", "type": "int"}, 
                                       {"name": "y", "type": ["boolean", "null"]},
                                       {"name": "e", "type": {"type": "enum", "name": "Test", "symbols": ["A", "B", "C"]}}
                                    ]}, "input")
        self.assertEqual(field, [("x", "int"), ("y", "boolean,null"), ("e", "enum")])
        self.assertEqual(type, True)

        field, type = getPFAField({"type": "record", "name": "Input", 
                                   "fields": [
                                       {"name": "a", "type": {"type": "array", "items": "double"}},
                                    ]}, "input")
        self.assertEqual(field, [("a", "array")])
        self.assertEqual(type, True)

    def test_asserts07(self):
        self.assertRaisesRegexp(NotImplementedError, 
                                "record, map, array, enum are not supported in union",
                                lambda: getPFAField({"type": "record", "name": "Input", 
                                                    "fields": [
                                                        {"name": "x", "type": "int"}, 
                                                        {"name": "y", "type": ["boolean", "null", {"type": "enum", "name": "Test", "symbols": ["A", "B", "C"]}]}
                                                    ]}, "input"))

    def test_asserts08a(self):
        self.assertRaisesRegexp(NotImplementedError, 
                        " is not supported",
                        lambda: getPFAField({"type": "record", "name": "Input", 
                                            "fields": [
                                                {"name": "x", "type": "int"}, 
                                                {"name": "y", "type": ["boolean", "null"]},
                                                {"name": "a", "type": {"type": "map", "values": "double"}},
                                            ]}, "input"))        

    def test_asserts08b(self):        
        self.assertRaisesRegexp(NotImplementedError, 
                        " is not supported.",
                        lambda: getPFAField({"type": "record", "name": "Input", 
                                            "fields": [
                                                {
                                                    "type": "record",
                                                    "name": "MyRecord",
                                                    "fields": [
                                                        {"name": "one", "type": "int"},
                                                        {"name": "two", "type": "double"},
                                                        {"name": "three", "type": "string"}
                                                    ]
                                                },
                                            ]}, "input")) 

    def test_asserts08c(self):
        self.assertRaisesRegexp(NotImplementedError, 
                        " is not supported.",
                        lambda: getPFAField({"type": "record", "name": "Input", 
                                            "fields": [
                                                {"name": "x", "type": set("int")}, 
                                                {"name": "y", "type": tuple(["boolean", "null", {"type": "enum", "name": "Test", "symbols": ["A", "B", "C"]}])}
                                                ]}, "input"))        

    def test_asserts09(self):
        self.assertRaisesRegexp(NotImplementedError, 
                "Field with datatype 'array' is not supported in the",
                lambda: getPFAField({"type": "record", "name": "Input", 
                                   "fields": [
                                       {"name": "x", "type": "int"}, 
                                       {"name": "y", "type": ["boolean", "null"]},
                                       {"name": "a", "type": {"type": "array", "items": "double"}},
                                       {"name": "e", "type": {"type": "enum", "name": "Test", "symbols": ["A", "B", "C"]}}
                                    ]}, "input"))                                                                                 

    def test_asserts10(self):
        self.assertRaisesRegexp(NotImplementedError, 
                                "'record', 'enum' and 'array' datatype for ",
                                lambda: getPFAField({"type": "unknown", "name": "Unknown"}, "input"))

class ScoringModelTests(unittest.TestCase):
    def test_01(self):
        model = ScoringModel.fromPMML("""<?xml version="1.0" encoding="UTF-8"?>
<PMML version="4.1" xmlns="http://www.dmg.org/PMML-4_1">
  <Header copyright="KNIME">
    <Application name="KNIME" version="2.8.0"/>
  </Header>
  <DataDictionary numberOfFields="5">
    <DataField name="sepal_length" optype="continuous" dataType="double">
      <Interval closure="closedClosed" leftMargin="4.3" rightMargin="7.9"/>
    </DataField>
    <DataField name="sepal_width" optype="continuous" dataType="double">
      <Interval closure="closedClosed" leftMargin="2.0" rightMargin="4.4"/>
    </DataField>
    <DataField name="petal_length" optype="continuous" dataType="double">
      <Interval closure="closedClosed" leftMargin="1.0" rightMargin="6.9"/>
    </DataField>
    <DataField name="petal_width" optype="continuous" dataType="double">
      <Interval closure="closedClosed" leftMargin="0.1" rightMargin="2.5"/>
    </DataField>
    <DataField name="class" optype="categorical" dataType="string">
      <Value value="Iris-setosa"/>
      <Value value="Iris-versicolor"/>
      <Value value="Iris-virginica"/>
    </DataField>
  </DataDictionary>
  <TreeModel modelName="DecisionTree" functionName="classification" splitCharacteristic="binarySplit" missingValueStrategy="lastPrediction" noTrueChildStrategy="returnNullPrediction">
    <MiningSchema>
      <MiningField name="sepal_length" invalidValueTreatment="asIs"/>
      <MiningField name="sepal_width" invalidValueTreatment="asIs"/>
      <MiningField name="petal_length" invalidValueTreatment="asIs"/>
      <MiningField name="petal_width" invalidValueTreatment="asIs"/>
      <MiningField name="class" invalidValueTreatment="asIs" usageType="predicted"/>
    </MiningSchema>
    <Node id="0" score="Iris-setosa" recordCount="150.0">
      <True/>
      <ScoreDistribution value="Iris-setosa" recordCount="50.0"/>
      <ScoreDistribution value="Iris-versicolor" recordCount="50.0"/>
      <ScoreDistribution value="Iris-virginica" recordCount="50.0"/>
      <Node id="1" score="Iris-setosa" recordCount="50.0">
        <SimplePredicate field="petal_width" operator="lessOrEqual" value="0.6"/>
        <ScoreDistribution value="Iris-setosa" recordCount="50.0"/>
        <ScoreDistribution value="Iris-versicolor" recordCount="0.0"/>
        <ScoreDistribution value="Iris-virginica" recordCount="0.0"/>
      </Node>
      <Node id="2" score="Iris-versicolor" recordCount="100.0">
        <SimplePredicate field="petal_width" operator="greaterThan" value="0.6"/>
        <ScoreDistribution value="Iris-setosa" recordCount="0.0"/>
        <ScoreDistribution value="Iris-versicolor" recordCount="50.0"/>
        <ScoreDistribution value="Iris-virginica" recordCount="50.0"/>
        <Node id="3" score="Iris-versicolor" recordCount="54.0">
          <SimplePredicate field="petal_width" operator="lessOrEqual" value="1.7"/>
          <ScoreDistribution value="Iris-setosa" recordCount="0.0"/>
          <ScoreDistribution value="Iris-versicolor" recordCount="49.0"/>
          <ScoreDistribution value="Iris-virginica" recordCount="5.0"/>
        </Node>
        <Node id="10" score="Iris-virginica" recordCount="46.0">
          <SimplePredicate field="petal_width" operator="greaterThan" value="1.7"/>
          <ScoreDistribution value="Iris-setosa" recordCount="0.0"/>
          <ScoreDistribution value="Iris-versicolor" recordCount="1.0"/>
          <ScoreDistribution value="Iris-virginica" recordCount="45.0"/>
        </Node>
      </Node>
    </Node>
  </TreeModel>
</PMML>""")
        self.assertEqual(model.type, "PMML")
        self.assertEqual(model.inputFields, [('sepal_length', 'double'), ('sepal_width', 'double'), ('petal_length', 'double'), ('petal_width', 'double')])
        self.assertEqual(model.outputFields, [('predicted_class', 'string'), ('probability', 'real'), ('probability_Iris-setosa', 'real'), 
                                              ('probability_Iris-versicolor', 'real'), ('probability_Iris-virginica', 'real'), ('node_id', 'string')])
        self.assertEqual(model.targetFields, [('class', 'string')])

    def test_02(self):
        model = ScoringModel.fromPFA("""{
    "input": "double",
    "output": "double",
    "action": [
      {"+": ["input", 100]}
    ]
}""", ".json")
        self.assertEqual(model.type, "PFA")
        self.assertEqual(model.inputFields, [('input_value', 'double'),])
        self.assertEqual(model.outputFields, [('output_value', 'double'),])

    def test_03(self):
        model = ScoringModel.fromPFA("""
input: {type: array, items: double}
output: string
cells:
  clusters:
    type:
      type: array
      items:
        type: record
        name: Cluster
        fields:
          - {name: center, type: {type: array, items: double}}
          - {name: id, type: string}
    init:
      - {id: one, center: [1, 1, 1, 1, 1]}
      - {id: two, center: [2, 2, 2, 2, 2]}
      - {id: three, center: [3, 3, 3, 3, 3]}
      - {id: four, center: [4, 4, 4, 4, 4]}
      - {id: five, center: [5, 5, 5, 5, 5]}
action:
  attr:
    model.cluster.closest:
      - input
      - cell: clusters
      - params:
          - x: {type: array, items: double}
          - y: {type: array, items: double}
        ret: double
        do:
          metric.euclidean:
            - fcn: metric.absDiff
            - x
            - y
  path: [[id]]""", ".yaml")
        self.assertEqual(model.type, "PFA")
        self.assertEqual(model.inputFields, [('input_value', 'array of double'),])
        self.assertEqual(model.outputFields, [('output_value', 'string'),])

class ReaderTests(unittest.TestCase):
    def test_01(self):
        pmmlFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sample_pmml.xml")
        self.assertEqual(PMMLFormat.get_reader(pmmlFile).read().type, "PMML")

    def test_02(self):
        pfaFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sample_pfa.json")
        self.assertEqual(PFAFormat.get_reader(pfaFile).read().type, "PFA")

class TestOWLoadModel(WidgetTest):
    def setUp(self):
        self.widget = self.create_widget(OWLoadModel)
        self.pfaFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sample_pfa.json")
        self.pmmlFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "sample_pmml.xml")

    def test_describe_pfa(self):
        self.assertEqual(
            OWLoadModel._describe(PFAFormat.get_reader(self.pfaFile).read()), 
            'Method:<br/>&nbsp;&nbsp;&nbsp;&nbsp;map<br/>Input fields(s):<br/>&nbsp;&nbsp;&nbsp;&nbsp;input_value (double)<br/>Output fields(s):<br/>&nbsp;&nbsp;&nbsp;&nbsp;output_value (double)')

    def test_describe_pmml(self):
        self.assertEqual(
            OWLoadModel._describe(PMMLFormat.get_reader(self.pmmlFile).read()), 
            'Input fields(s):<br/>&nbsp;&nbsp;&nbsp;&nbsp;sepal_length (double), sepal_width (double), petal_length (double), petal_width (double)<br/>Output fields(s):<br/>&nbsp;&nbsp;&nbsp;&nbsp;cluster (string), cluster_name (string), distance (real)<br/>Target fields(s):<br/>&nbsp;&nbsp;&nbsp;&nbsp;None')