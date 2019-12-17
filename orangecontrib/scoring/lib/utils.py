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

def prettifyText(fieldList, pre='', sep=", ", size=80):
    l = len(pre)
    lines = []
    currentLine = [pre]
    for item in fieldList:
        if l + len(item + sep) > size:
            lines.append(''.join(currentLine))
            currentLine = [item, sep]
            l = len(item + sep)
        else:
            currentLine.append(item)
            currentLine.append(sep)
            l += len(item + sep)
    if len(currentLine)>0:
        if currentLine[-1] == sep:
            currentLine = currentLine[:-1]
        lines.append(''.join(currentLine))
    return lines
