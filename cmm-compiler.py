import os
import sys

CMMLIB_PATH = ""

class LangStream():
    baselib = """
#include <stdio.h>
#include <stdint.h>

void printstr(char *toPrint) {
    printf(toPrint);
}
"""

    cc = ""
    src = ""
    secs = {}
    ongoing = None

    scache = ""
    
    varstr = ""
    fnstr = ""
    treestr = ""
    gstr = ""

class SLangStream():
    fn = None
    fnclosed = True

    externc = None
    externcclosed = True

    tree = None
    treeclosed = True

def getTypeEquivalent(_type: str):
    if _type == "string":
        return "char*"
    if _type == "int":
        return "int"
    if _type == "uint":
        return "unsigned int"
    if _type == "uint8":
        return "uint8_t"
    if _type == "uint16":
        return "uint16_t"
    if _type == "uint32":
        return "uint32_t"
    if _type == "any":
        return "void*"

    if _type.startswith("_ctype/"):
        return _type.split("/")[1]

def toASM_FN(line: str):
    sstr = line.strip().replace("\t", "").split(" ")
    if not sstr: sstr = None
    ins = line.strip().replace("\t", "")
    if sstr: ins = sstr[0]

    if ins == "ret" or line.strip().replace("\t", "").startswith("ret"):
        sb = ""
        if sstr:
            for i in range(sstr.__len__()):
                if i == 0: continue
                sb += sstr[i]
        
        return f"return {sb};"
    
    if ins == "_c":
        sb = ""
        for i in range(sstr.__len__()):
            if i == 0: continue
            sb += sstr[i]
        return sb
    
    if ins == "var":
        name0 = line.strip().replace("\t", "").replace(" ", "").split("var")[1].split(":")
        if line.__contains__("="): name0 = line.strip().replace("\t", "").replace(" ", "").split("var")[1].split("=")[0].split(":")
        name = name0[0]
        _vartype = getTypeEquivalent(name0[1])
        #content = line.strip().replace("\t", "").replace(" ", "").split("=")[1]
        #sb = content

        sb = "="+line.strip().replace("\t", "").split("=")[1] if line.__contains__("=") else ""
        return f"{_vartype} {name}{sb};"
    
    if ins == "call":
        fnname = sstr[1]
        if sstr.__len__() == 2:
            return f"{fnname}()"
        
        content = line.strip().replace(" ", "").split(fnname)[1]
        argsbase = content.split(",")
        argbuilder = ""
        suffix = ", "
        for i in range(argsbase.__len__()):
            if i == argsbase.__len__()-1: suffix = ""
            argbuilder += f" {argsbase[i]}{suffix} "
        return f"{fnname}( {argbuilder} );"

    return line

def toASM_TREE(line: str):
    sstr = line.strip().replace("\t", "").split(" ")
    if not sstr: sstr = None
    ins = line.strip().replace("\t", "")
    if sstr: ins = sstr[0]

    if ins == "var":
        name0 = line.strip().replace("\t", "").replace(" ", "").split("var")[1].split(":")
        if line.__contains__("="): name0 = line.strip().replace("\t", "").replace(" ", "").split("var")[1].split("=")[0].split(":")
        name = name0[0]
        _vartype = getTypeEquivalent(name0[1])
        #content = line.strip().replace("\t", "").replace(" ", "").split("=")[1]
        #sb = content

        sb = "="+line.strip().replace("\t", "").split("=")[1] if line.__contains__("=") else ""
        return f"{_vartype} {name}{sb};"
    return line

def generate_line(line: str, s: LangStream, ss: SLangStream, lineIndex: int, prevLine: str):
    sstr = line.replace("\t", "").split(" ")
    if not sstr: sstr = None
    ins = line.strip().replace("\t", "")
    if sstr: ins = sstr[0]

    if line.strip().replace(" ", "").startswith("}fn"): ss.fnclosed = True; s.fnstr += "\n}"
    if not ss.fnclosed:
        s.fnstr += "\n\t"+toASM_FN(line)
    
    if line.strip().replace(" ", "").startswith("}tree"): ss.treeclosed = True; s.treestr += f"\n{'}'} {ss.tree}"
    if not ss.treeclosed:
        s.treestr += "\n\t"+toASM_TREE(line)
    
    if ss.fnclosed and ss.treeclosed:
        if ins == "var":
            s.varstr += f"\n{toASM_FN(line)}"
        
        elif ins == "public":
            if sstr[1] == "fn":
                name = sstr[2]
                if name == "main": name = "main"

                prefix = "" if name == "main" else "CMINUSMINUS_"
                s.fnstr += f"\n{prefix}{name}{'{'}"
                s.gstr += name

                if line.strip().replace(" ", "").endswith("{"):
                    ss.fn = name
                    ss.fnclosed = False

        elif ins == "fn":
            name = sstr[1]
            if name.__contains__(":"): name = name.split(":")[0]

            fntype = "int" if name == "main" else "void"
            if line.__contains__(":"):
                content = line.strip().replace(" ", "").split(name)[1]
                fntype = getTypeEquivalent(content.split(":")[1].split("{")[0])
            
            if prevLine.strip().replace(" ", "").startswith("@") and ins == "fn":
                content = prevLine.strip().replace(" ", "").split("@")[1]
                argsbase = content.split(",")
                args = {}
                argbuilder = ""
                suffix = ", "
                for i in range(argsbase.__len__()):
                    arg = argsbase[i].split(":")
                    if i == argsbase.__len__()-1: suffix = ""
                    argbuilder += f" {getTypeEquivalent(arg[1])} {arg[0]}{suffix}"
                    args.update({arg[0]: arg[1]})
                
                prefix = "" #if name == "main" else "CMINUSMINUS_"
                s.fnstr += f"\n{fntype} {prefix}{name}( {argbuilder} ){'{'}"
            else:
                prefix = "" #if name == "main" else "CMINUSMINUS_"
                s.fnstr += f"\n{fntype} {prefix}{name}(){'{'}"

            if line.strip().replace(" ", "").endswith("{"):
                ss.fn = name
                ss.fnclosed = False

                #s.varstr += f"\n\tCMMFN_ARG_{arg[0]} db \"{arg[1]}\", 0"
        
        elif ins == "tree":
            name = sstr[1]
                
            s.treestr += f"\ntypedef struct {'{'}"
            if line.strip().replace(" ", "").endswith("{"):
                ss.tree = name
                ss.treeclosed = False
    s.cc = f"""
{s.baselib}
{s.treestr}
{s.varstr}
{s.fnstr}
"""



stream = LangStream()

sstream = SLangStream()

fc_src = ""

with open("main.cmm") as f:
    fc_src = f.read()
    f.close()

stream.src = fc_src

for i in range(stream.src.split("\n").__len__()):
    if i<1: generate_line(stream.src.split("\n")[i], stream, sstream, i, stream.src.split("\n")[i]); continue
    generate_line(stream.src.split("\n")[i], stream, sstream, i, stream.src.split("\n")[i-1])
    print(sstream.fnclosed)

print(stream.cc)
with open("main.c", "w") as f:
    f.write(stream.cc)
    f.close()
