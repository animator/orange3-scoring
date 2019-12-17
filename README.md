Orange3 Scoring
======================

This is an scoring/inference add-on for [Orange3](http://orange.biolab.si). This add-on adds widgets to
load [PMML](http://dmg.org/pmml/v4-4/GeneralStructure.html) and [PFA](http://dmg.org/pfa/index.html) models 
and score data.

## Dependencies
To use PMML models make sure you have Java installed:
 - Java >= 1.8
 - pypmml (downloaded during installation)

To use PFA models:
 - titus2 (downloaded during installation)

Installation
------------

To install the add-on using pip, run
```
    pip install orange3-scoring
```
To register this add-on with Orange, but keep the code in the development directory (do not copy it to 
Python's site-packages directory), run
```
    pip install -e .
```

Usage
-----

After the installation, the widget from this add-on is registered with Orange. To run Orange from the terminal,
use
```
    python -m Orange.canvas
```
The new widget appears in the toolbox bar under the section Example.

![screenshot](https://github.com/animator/orange3-scoring/blob/master/screens/screenshot.png)
