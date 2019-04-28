# !/usr/bin/env python3
import re
import sys
import fileinput
import os
from pathlib import Path
from shutil import copyfile
from collections import defaultdict


from collections import Counter


# Open the tamarin file
# Remove all newline characters in premise/action labels or conclusions
## Adds session ID to all premises and conclusions
## Also adds session IDs to all the action labels
## Adds all the required restrictions for the rules
# Rules for TAMARIN file to be processed :
#     All protocol rules must be numbered 1,2,3,..,n and should be placed in sequence in the file
#     The action labels must have distinct names
#      Fact and action label names must also be distinct
#     Comments inside the rule /lemma will be removed
#     Uses user-defined  action labels of the form "Log<PartID>[0-9]+" for stealth check
#	Performs stealth check against global log  as well as individual participant's log


def Add_session_id_to_premise(file_name, tag1, tag2):
    with fileinput.input(files=(file_name), inplace=True) as text_file:
        for line in text_file:
            # split the line into groups
            # If there is a rule statement
            rulematch = re.match(r"(rule)(.*)([0-9])(.*):(.*)(\[.*\])(.*)(\-\-)", line)
            if rulematch:
                matches = re.match(r"(rule)(.*?)([0-9]+)(.*)(\[.*\])(.*)(\-\-)", line)
                # Check rule again and stop at rule number
                if matches:
                    premise = matches.group(5)[1:-1]
                    rule_number = matches.group(3)
                    # Third group contains rule number
                    if (rule_number == "1"):
                        # If it is first rule, add tag1 for adding fresh session ID to premise
                        # create a new [..] string with the prepended tag
                        modified_premise = "[{},{}]".format(tag1, premise.strip())
                        modified_premise = modified_premise.replace(",]", "]")
                    else:
                        # If it is any other rule than first , add tag2 for adding Input session ID to premise
                        # create a new [..] string with the prepended tag
                        modified_premise = "[{},{}]".format(tag2, premise.strip())
                        modified_premise = modified_premise.replace(",]", "]")
                # replace the original [..] with the modified [..]
                modified_line = line.replace(matches.group(5), modified_premise)
                # print out the modified line to the file
                print(modified_line, end="")
            else:
                print(line, end="")


# It is modifying the first rule it finds, we want the first numbered rule i.e. rule 1 to be modified : SUCCESS
def Add_session_id_to_first_conclusion(file_name, tag1):
    input = open(file_name, "r")
    output = open("final.txt", "w+")
    text = input.read()
    rulematch = re.search(r'(rule).*([0-9]+).*:.*(\[.*\])(\s*)\-\-(\s*)(\[.*\])(\s*)\-\>(\s*)(\[.*])', text)
    if rulematch:
        conclusion = rulematch.group(9)[1:-1]
        rule_number = rulematch.group(2)
        if (rule_number == "1"):
            modified_concl = "[{},{}]".format(tag1, conclusion.strip())
            modified_concl=modified_concl.replace(",]","]")
            modified_line = text.replace(rulematch.group(9), modified_concl)
            # print(modified_line, end="")
            output.write(modified_line + "")
        else:
            # print(text, end="")
            output.write(text + "")
    else:
        # print(text, end="")
        output.write(text + "")

# Working : Updating only LogXn labels
def Add_session_id_to_Stealth_Logs(file_name):
    with fileinput.FileInput(file_name, inplace=True) as file:
        for line in file:
            match = re.search(r'(rule)(.*)([0-9]+).*:.*(\[.*\])(\s*)\-\-(\s*)(\[.*\])(\s*)\-\>', line, re.MULTILINE)
            if match:
                TempActionLabels = match.group(7)
                ActionLabels=TempActionLabels.replace(" ","")
                rule_number = match.group(3)
                if (rule_number == "1"):
                    # Search for Log
                    LogSearch = re.findall(r'Log[A-Z][0-9]+\(.*?\)',ActionLabels)
                    if LogSearch:
                        for i in range(0,len(LogSearch)):
                            oldLogLabels=LogSearch[i]
                            ModifiedLogLabels = re.sub(r'\(', '(~sid,', LogSearch[i])
                            ModifiedActionLabels=ActionLabels.replace(oldLogLabels,ModifiedLogLabels)
                            ActionLabels = ModifiedActionLabels
                        tmpline = line.replace(match.group(7), ModifiedActionLabels)
                        # To handle if there is any parameter in action labels or not
                        newline = tmpline.replace("(,","(")
                        print(newline, end="")
                    else:
                        StActionLabel ="Log"
                        ## Form the stealthy log by adding player initial and seq no e.g. LogI1, LogR3 etc..
                        player = match.group(2)
                        seqno = match.group(3)
                        StActionLabel = StActionLabel + player.strip()[:1] + seqno.strip() + "(~sid)"
                        ActionLabels = TempActionLabels.replace("[", "[" + StActionLabel + ",")
                        tmpline = line.replace(match.group(7), ActionLabels)
                        newline = tmpline.replace(",]", "]")
                        print(newline, end="")
                else:
                    # Search for Log
                    LogSearch = re.findall(r'Log[A-Z][0-9]+\(.*?\)', ActionLabels)
                    if LogSearch:
                        for i in range(0,len(LogSearch)):
                            oldLogLabels=LogSearch[i]
                            ModifiedLogLabels = re.sub(r'\(', '(sid,', LogSearch[i])
                            ModifiedActionLabels=ActionLabels.replace(oldLogLabels,ModifiedLogLabels)
                            ActionLabels = ModifiedActionLabels
                        tmpline = line.replace(match.group(7), ModifiedActionLabels)
                        # To handle if there is any parameter in action labels or not
                        newline = tmpline.replace("(,","(")
                        print(newline, end="")
                    else:
                        StActionLabel = "Log"
                           ## Form the stealthy log by adding player initial and seq no e.g. LogI1, LogR3 etc..
                        player = match.group(2)
                        seqno = match.group(3)
                        StActionLabel = StActionLabel + player.strip()[:1] + seqno.strip() + "(sid)"
                        ActionLabels = TempActionLabels.replace("[", "[" + StActionLabel + ",")
                        tmpline = line.replace(match.group(7), ActionLabels)
                        newline = tmpline.replace(",]", "]")
                        print(newline, end="")
            else:
                print(line, end="")



def getAlabelList(line):
    # """
    # Assumes comma separated, and opens and closes with square brackets
    # """
    line = line[1:-1]  # strip square brackets
    funcs = []

    current = ""
    brack_stack = 0  # we don't want to follow comma's if they are in a function
    for char in line:
        if char == "(":
            brack_stack += 1
        elif char == ")":
            brack_stack -= 1

        if char == "," and brack_stack == 0:
            # new function, clear current and append to list
            funcs.append(current)
            current = ""
        else:
            current += char
    #  Append only if there is at least one label else leave it as it is (blank)
    if current:
        funcs.append(current)
    return funcs



def getAlabelNames(line):
    # """
    # Assumes comma separated, and opens and closes with square brackets
    # """
    line = line[1:-1]  # strip square brackets
    alnames = []

    current = ""
    brack_stack = 0  # we don't want to follow comma's if they are in a function
    for char in line:
        if char == "(" and brack_stack == 0:
            # First bracket found, add al name to list and clear current
            alnames.append(current)
            current=""
            brack_stack += 1
        elif char == ")":
            current=""
            brack_stack -= 1

        if char == "," and brack_stack == 0:
            # new function, clear current
            current = ""
        elif not(char == ")"):
            current += char

    return alnames

def Split_action_labels(file_name, rulewise_action_labels):
    with fileinput.input(files=(file_name), inplace=True) as text_file:
        current_rule = -1
        for line in text_file:
            print(line.rstrip())
            # split the line into groups
            matches = re.match(r"(rule)(.*)[0-9]+(.*):(.*)(\-\-)(\[.*\])(\-\>)(.*)", line)
            if matches:
                current_rule += 1
                action_label_list = matches.group(6)
                ## Clean action labels by removing $ and ~ used by tamarin
                action_label_list = action_label_list.replace("$", "").replace("~", "")
                all_action_labels = (getAlabelList(action_label_list))
                rulewise_action_labels.append([])
                for j, x in enumerate(all_action_labels, 1):
                    ## Add action label to the list
                    rulewise_action_labels[current_rule].append(x)
    return rulewise_action_labels

#Forms a list of unique action labels used in the numbered rules
def numbered_action_labels(file_name):
    with fileinput.input(files=(file_name), inplace=True) as text_file:
        current_rule = -1
        action_label_names=[]
        for line in text_file:
            print(line.rstrip())
            # split the line into groups
            numbered_rule = re.match(r"(rule)(.*)[0-9]+(.*):(.*)(\-\-)(\[.*\])(\-\>)(.*)", line)
            if numbered_rule:
                current_rule += 1
                action_label_list = numbered_rule.group(6)
                ## Clean action labels by removing $ and ~ used by tamarin
                action_label_list = action_label_list.replace("$", "").replace("~", "")
                all_action_labels = (getAlabelNames(action_label_list))
                action_label_names.append(all_action_labels)

    uniqueAL = [item for sublist in action_label_names for item in sublist]
    set_uniqueAL=set(uniqueAL)
    return set_uniqueAL
    # uniqueALlist=list(set_uniqueAL)
    # return uniqueALlist


#Forms a list of unique action labels used in the numbered rules
def complete_list__action_labels(file_name):
    with fileinput.input(files=(file_name), inplace=True) as text_file:
        current_rule = -1
        action_label_names=[]
        for line in text_file:
            print(line.rstrip())
            # split the line into groups
            numbered_rule = re.match(r"(rule)(.*):(.*)(\-\-)(\[.*\])(\-\>)(.*)", line)
            if numbered_rule:
                current_rule += 1
                action_label_list = numbered_rule.group(5)
                ## Clean action labels by removing $ and ~ used by tamarin
                action_label_list = action_label_list.replace("$", "").replace("~", "")
                all_action_labels = (getAlabelNames(action_label_list))
                action_label_names.append(all_action_labels)

    uniqueAL = [item for sublist in action_label_names for item in sublist]
    set_uniqueAL=set(uniqueAL)
    return set_uniqueAL

####### Remove comments within rule outside of rule premises / action labels / conclusions brackets
def clean_tamarin_file(file_name):
    tamarin_input = open(file_name)
    output = open("temp.txt", "w")
    line  = tamarin_input.read()
    # Remove comments between premise and action label
    match = re.findall(r'\]\s*(.[^\[]*)\s*\-\-', line, re.MULTILINE)
    if match:
        for i in range(0, len(match)):
            content = match[i]
            multilinecomment = re.findall(r'/\*.*?\*/', content)
            if multilinecomment:
                for j in range(0, len(multilinecomment)):
                    newline = line.replace(multilinecomment[j], "")
                    line = newline
    # Remove comments between   action label and conclusion
    match1 = re.findall(r'\]\-\>\s*.*\s*\[', line, re.MULTILINE)
    if match1:
        for i in range(0, len(match1)):
            content1 = match1[i]
            multilinecomment1 = re.findall(r'/\*.*?\*/', content1)
            if multilinecomment1:
                for j in range(0, len(multilinecomment1)):
                    newline = line.replace(multilinecomment1[j], "")
                    line = newline

    output.write(line)
    tamarin_input.close()
    output.close()

######## Bring all rules / lemmas in one line
def format_tamarin_file(file_name):
    ######## Remove newline within rule premises / action labels / conclusions
    tamarin_input = open(file_name)
    output = open("ready.txt", "w")
    text = tamarin_input.read()
    # Remove all occurance singleline comments (//COMMENT\n ) from file
    text = re.sub(re.compile("//.*?\n"), "", text)
    # Remove all newline characters appearing between brackets opening and closing
    text = re.sub(r'\[.*?\]', lambda m: m.group().replace("\n", ""), text, flags=re.DOTALL)
    #
    # # ######## Remove tabs within rule premises / action labels / conclusions
    text = re.sub(r'\[.*?\]', lambda m: m.group().replace("\t", ""), text, flags=re.DOTALL)
    #
    # # ######## To ignore rule if it is part of comment : only remove newline if is not part of comment
    text = re.sub(r'(rule).[^\\\*]*?\[', lambda m: m.group().replace("\n", ""), text, flags=re.DOTALL)
    # #
    # # # ######## Remove newline and tabs between  rule premises and  action labels
    text = re.sub(r'\]\s*\-\-', lambda m: m.group().replace("\n", ""), text, flags=re.MULTILINE)
    # #
    # # ###Remove spaces between parameters [..]
    text = re.sub(r'\[.*?\]', lambda m: m.group().replace(" ", ""), text, flags=re.DOTALL)
    # #

    # # #### Format restriction  to one line
    text = re.sub(r'(restriction)(.*?\s*?:)(.*\s*)(.*\s*)?(")', lambda m: m.group().replace("\n", ""), text,
                  flags=re.MULTILINE)
    # # #### Format lemmas to one line
    text = re.sub(r'(restriction)(.*?\s*?:)(.*\s*)(.*\s*)?(")', lambda m: m.group().replace("\t", ""), text,
                  flags=re.MULTILINE)

    # # #### Format lemmas to one line
    text = re.sub(r'(lemma)(.*?\s*?:)(.*\s*)(.*\s*)?"(.*\s*)*?.*"', lambda m: m.group().replace("\n", ""), text,
                  flags=re.MULTILINE)
    # # #### Format lemmas to one line
    text = re.sub(r'(lemma)(.*?\s*?:)(.*\s*)(.*\s*)?"(.*\s*)*?.*"', lambda m: m.group().replace("\t", ""), text,
                  flags=re.MULTILINE)
    # # #### Format lemmas : remove space
    text = re.sub(r'(lemma)(.*?\s*?:)(.*\s*)(.*\s*)?"(.*\s*)*?.*"', lambda m: m.group().replace("[a-zA-Z].*(", "("), text,
                  flags=re.MULTILINE)
    # # #### Format lemmas to one line
    text = re.sub(r'(lemma)(.*?\s*?:)(.*\s*)(.*\s*)?"(.*\s*)*?.*"', lambda m: m.group().replace("( ", "("), text,
                  flags=re.MULTILINE)
    # # ######## Remove newline  between  action labels and  conclusions
    output.write(re.sub(r'\-\>\s*\[', lambda m: m.group().replace("\n", ""), text, flags=re.MULTILINE))
    tamarin_input.close()
    output.close()

def remove_multiline_comments_from_rules(file_name):
    with fileinput.FileInput(file_name, inplace=True) as file:
        for line in file:
            # Just extract the whole lemma
            match = re.search(r'\[(.*)?\]', line, re.MULTILINE)
            if match:
                content = match.group(1)
                multilinecomment = re.findall(r'/\*.*?\*/', content)
                if multilinecomment:
                    for j in range(0, len(multilinecomment)):
                        newline = line.replace(multilinecomment[j], "")
                        line = newline
                print(line, end="")
            else:
                print(line,end="")


def remove_multiline_comments_from_lemma(file_name):
    with fileinput.FileInput(file_name, inplace=True) as file:
        for line in file:
            # Just extract the whole lemma
            match = re.search(r'lemma.*?:.*?"(.*)?"', line, re.MULTILINE)
            if match:
                comment = match.group(1)
                matchagain = re.findall(r'/\*.*?\*/', comment)
                if matchagain:
                    for j in range(0, len(matchagain)):
                        newline = line.replace(matchagain[j], "")
                        line = newline
                print(line, end="")
            else:
                print(line,end="")



def Extract_parameters(label):
    newpars=''
    if  label :
        matches = re.search(r'\((.*)\)', label)
        allpars = matches.group(0)[1:-1]
        newpars = re.sub(r',', ' ', allpars)
        modifiedpars = re.findall(r'\<.*?\>', newpars)
        if modifiedpars:
            for i in range(0, len(modifiedpars)):
                str = "params" + (i + 1).__str__()
                finalpars = re.sub(modifiedpars[i], str, newpars)
                newpars = finalpars
        return newpars


def combine_common_pars(pars1, pars2):
    commonpars = ' '.join(set(pars1.split()).union(set(pars2.split())))
    return commonpars


def differce_of_pars(pars1, pars2):
    diffpars = ' '.join(set(pars1.split()).difference(set(pars2.split())))
    return diffpars


# Modifying for all previous action labels in one restr : Working : Jan 8, 2019
def construct_correspondence_restriction(prev_label_in, current_label_in,restnum):
    newpars1 =""
    newpars2 = ""
    current_label = ''.join(current_label_in[0].split())

    if current_label:
        currmatches = re.search(r'\((.*)\)', current_label)
        currparswithcomma = currmatches.group(0)[1:-1]
        currparswithspace = re.sub(r',', ' ', currparswithcomma)

    # Prepare the starting line for restriction
    matches = re.search(r'.*?\(', current_label)
    currname = matches.group(0)[:-1]
    currname.strip()
    reststr = ""
    restname = 'EveryALBefore' + currname + '_' + restnum.__str__()
    restname.strip(" ")
    reststr += "restriction "
    reststr = reststr + restname + ":" + "\n " + "\"All  " + currparswithspace + "  #i1.  " + currname + "(" + currparswithcomma + " )" + "@i1 ==>  ("
    restpart=""

    logtime=1

    # After finding combined parameters, its time to construct the restrictions by processing each action label
    for labels in range(len(prev_label_in) - 1, -1, -1):
        if (labels > -1):
            prev_label = ''.join(prev_label_in[labels][0].split())
            if prev_label:
                prevmatches = re.search(r'\((.*)\)', prev_label)
                prevparswithcomma = prevmatches.group(0)[1:-1]
                prevparswithspace = re.sub(r',', ' ', prevparswithcomma)
                matches = re.search(r'.*?\(', prev_label)
                prevname = matches.group(0)[:-1]
                prevname.strip()

                prevlogtime=logtime+1

                # We will now find differnce of  parameters between  current  and previous  action labels
                Expars = differce_of_pars(prevparswithspace,currparswithspace)

                restpart= " Ex " + Expars + "  #i"+prevlogtime.__str__()+".  " + prevname + "(" + prevparswithcomma + " )" + " @i"+prevlogtime.__str__()+" & (i"+prevlogtime.__str__()+" < i"+logtime.__str__()+") "

                reststr=reststr+restpart + "&"

                logtime=prevlogtime

    newlogtime=1

    # This part guarantees that each 'sid' can not be used by any  log more than once.
    # Starts with the last log
    curr_label = ''.join(current_label_in[0].split())
    if curr_label:
        currmatches = re.search(r'\((.*)\)', curr_label)
        currparswithcomma = currmatches.group(0)[1:-1]
        currparswithspace = re.sub(r',', ' ', currparswithcomma)
        Pars = currparswithspace.replace(' ', newlogtime.__str__() + ',')
        Pars = Pars + newlogtime.__str__()
        finalPars = re.sub(r',', ' ', Pars)
        finalPars = finalPars.replace('sid' + newlogtime.__str__(), 'sid')
        finalParswithcomma=finalPars.replace(' ',',')
        finalPars = finalPars.replace('sid', '')

        matches = re.search(r'.*?\(', curr_label)
        logname = matches.group(0)[:-1]
        logname.strip()

        prevlogtime = logtime + 1

        restpart = " ( All " + finalPars + "  #i" + prevlogtime.__str__() + ".  " + logname + "(" + finalParswithcomma + " )" + " @i" + prevlogtime.__str__() + " ==>  (#i" + prevlogtime.__str__() + " = #i" + newlogtime.__str__() + ")) "

        reststr = reststr + restpart + "&"

        logtime = prevlogtime
        newlogtime += 1

    for labels in range(len(prev_label_in) - 1, -1, -1):
        if (labels > -1):
            curr_label = ''.join(prev_label_in[labels][0].split())
            if curr_label:
                currmatches = re.search(r'\((.*)\)', curr_label)
                currparswithcomma = currmatches.group(0)[1:-1]
                currparswithspace = re.sub(r',', ' ', currparswithcomma)
                Pars= currparswithspace.replace(' ',newlogtime.__str__()+',')
                Pars=Pars+newlogtime.__str__()
                finalPars=re.sub(r',',' ',Pars)
                finalPars=finalPars.replace('sid'+newlogtime.__str__(),'sid')
                finalParswithcomma = finalPars.replace(' ', ',')
                finalPars=finalPars.replace('sid','')

                matches = re.search(r'.*?\(', curr_label)
                logname = matches.group(0)[:-1]
                logname.strip()

                prevlogtime = logtime + 1


                restpart = "( All " + finalPars + "  #i" + prevlogtime.__str__() + ".  " + logname + "(" + finalParswithcomma + " )" + " @i" + prevlogtime.__str__() + " ==>  (#i" + prevlogtime.__str__() + " = #i" + newlogtime.__str__() + ")) "

                reststr = reststr + restpart + "&"

                logtime = prevlogtime
                newlogtime+=1

    if restpart=="":
        return ""
    else:
        return reststr[:-1]+")\""



def format_uniqueness_restriction(file_name, label1, label2, fresh, restnames):
    with fileinput.input(files=(file_name), inplace=True) as text_file:
        for line in text_file:
            matches = re.match(r"\s*(end)\s*", line)
            if matches:
                modified_line = line.replace("end", construct_uniqueness_restriction(label1,label2,fresh,restnames))
                print(modified_line)
                print("end")
            else:
                print(line, end="")

# The uniqueness restriction uses different names for all the parameters except sid
# It ensures that for a single sid, there will be only a single run of a rule.
def construct_uniqueness_restriction(label1,label2,fresh,restnum):
    # Handles duplicate names of action labels by generating numbered restrictions
    cleaned_label1 = ''.join(label1.split())
    #Get list of parameters for action label, these might contain duplicates if ALs use them twice
    outputpars1 = Extract_parameters(cleaned_label1.strip())
    # Format them using commas to be used in restricttions
    # To have the first set of parameters
    usingpars1 = outputpars1.replace(' ', '1,')
    # To add 1 to last parameter
    usingpars1=usingpars1+'1'
    usingpars1=usingpars1.replace(fresh+'1',fresh)

    parslist1 = usingpars1.replace(',', ' ')

    cleaned_label2 = ''.join(label2.split())
    outputpars2 = Extract_parameters(cleaned_label2.strip())
    # To have the second set of parameters
    usingpars2 = outputpars2.replace(' ', '2,')
    # To add 1 to last parameter
    usingpars2=usingpars2+'2'
    usingpars2 = usingpars2.replace(fresh+'2', fresh)
    parslist2 = usingpars2.replace(',', ' ')

    #Clean outputpars by removing duplicates
    uniquepars=' '.join(set(parslist1.split()))
    parslist2=parslist2.replace(' '+fresh+' ','  ')
    uniquepars= uniquepars +' '+ parslist2
    uniquepars=' '.join(set(uniquepars.split()))
    logname1 = re.search(r'.*?\(', label1)
    logname2 = re.search(r'.*?\(', label2)
    restnametmp1 = logname1.group(0)[:-1]
    restnametmp2 = logname2.group(0)[:-1]
    restname='Unique_'+ fresh + '_for' + restnametmp1.strip() + 'and'+restnametmp2.strip()
    reststr = ""
    reststr += "restriction "
    reststr = reststr + restname + ": " + "\n " + " \"All  " + uniquepars + "  #i #j.  " + restnametmp1.strip() + "(" + usingpars1 + " )" + " @i  & " + restnametmp2.strip() + "(" + usingpars2 + " )" + " @j ==> (sid1 = sid2)\" "
    return reststr


## Working : Dec 17

# Modifying on Dec 17 to have all previous action labels in one restriction only
def format_correspondence_restriction(file_name, prev_labels, current_label,restnum):
    with fileinput.input(files=(file_name), inplace=True) as text_file:
        for line in text_file:
            matches = re.match(r"\s*(end)\s*", line)
            if matches:
                modified_line = line.replace("end", construct_correspondence_restriction(prev_labels, current_label,restnum))
                print(modified_line)
                print("end")
            else:
                print(line, end="")


# Generating  restrictions among pairs of  action labels with common fresh values.
def add_uniqueness_restrictions_to_tamarin_file(file_name, freshRL, all_action_labels):
    uniquerestnum=1

    for label1 in all_action_labels:
        # Loop over labels to extract the fresh values generated by the rule and used in the logs with other logs
        for label in label1:
            # Add restrictions only if  non-empty label exists
            if label.strip():
                matches = re.search(r'.*?\(', label.strip())
                label_name = matches.group(0)[:-1]
                if label_name in freshRL:
                    currentfr=freshRL[label_name]
                    Frsize=len(currentfr)
                    for label2 in all_action_labels:
                        if (label1 != label2):
                            for newlabel in label2:
                                if newlabel.strip():
                                    matches1 = re.search(r'Log.*(.*?\))', newlabel.strip())
                                    s = matches1.group(0)
                                    parameters=s[s.find("(") + 1:s.find(")")].split(',')
                                    for i in range(Frsize):
                                        if currentfr[i]:
                                            if currentfr[i] in parameters:
                                                format_uniqueness_restriction(file_name, label,newlabel, currentfr[i], uniquerestnum)
        print(end="\n")


def Collect_fresh_from_premise(file_name,frList):
    with fileinput.input(files=(file_name), inplace=True) as text_file:
        for line in text_file:
            # split the line into groups
            # If there is a rule statement
            rulematch = re.match(r"(rule)(.*)([0-9])(.*):(.*)(\[.*\])(.*)(\-\-)", line)
            if rulematch:
                matches = re.match(r"(rule)(.*?)([0-9]+)(.*)(\[.*\])(.*)(\-\-)", line)
                # Check rule again and stop at rule number
                if matches:
                    rulename=matches.group(2)+matches.group(3)

                    premise = matches.group(5)[1:-1]
                    fresh=re.match(r"(Fr)(.*?\))",premise)
                    frSearch = re.findall(r'Fr(.*?\))',premise,re.DOTALL)

                    for match in re.finditer('Fr(.*?\))', premise, re.S):
                        freshValue = match.group(1).replace('(','').replace(')','').replace('~','')
                        fr = freshValue.strip()
                        idx="Log"+rulename.strip()
                        frList.setdefault(idx,[]).append(fr)
                print(line, end="")
            else:
                print(line, end="")
    return frList





# Adds all previous logs in single restriction : Updated Dec 17
def add_correspondence_restrictions_to_tamarin_file(file_name,all_action_labels):
    corrrestnum=1
    for lastAL in range(len(all_action_labels)-1,-1,-1):
        if (lastAL>0):
            # The currentAL represents the current action label for which all action labels must exist previously in the trace
            # denoted by allprevALs
            currentAL=all_action_labels[lastAL]
            allprevALs=all_action_labels[:lastAL]

            format_correspondence_restriction(file_name, allprevALs, currentAL, corrrestnum)
            corrrestnum += 1



def add_newline_before_rule(file_name):
    with fileinput.FileInput(file_name, inplace=True) as file:
        for line in file:
            # Just extract the whole lemma
            match = re.search(r'rule', line, re.MULTILINE)
            if match:
                newline = re.sub(r'rule', "\n" + "rule ", line)
                line = newline
                print(line, end="")
            else:
                print(line,end="")


def add_newline_before_lemmas(file_name):
    with fileinput.FileInput(file_name, inplace=True) as file:
        for line in file:
            # Just extract the whole lemma
            match = re.search(r'lemma.*?:.*?".*?"', line, re.MULTILINE)
            if match:
                newline = re.sub(r'(lemma)', "\n" + "lemma ", line)
                line = newline
                print(line, end="")
            else:
                print(line,end="")


def add_newline_before_restrictions(file_name):
    with fileinput.FileInput(file_name, inplace=True) as file:
        for line in file:
            # Just extract the whole lemma
            match = re.search(r'restriction.*?:.*?".*?"', line, re.MULTILINE)
            if match:
                newline = re.sub(r'(restriction)', "\n" + "restriction ", line)
                line = newline
                print(line, end="")
            else:
                print(line,end="")

# Select only Log labels for stealth check restrictions
def select_Log_labels(list1):
    tmplist = [[]]
    index = -1
    for row in list1:
        # Loop over columns.
        index += 1
        tmplist.append([])
        for column in row:
            # Add restrictions only if  non-empty label exists
            if "Log" in column.strip():
                tmplist[index].append(column.strip())

    Loglist = [x for x in tmplist if x != []]

    return Loglist

# Find all the participants
def return_players(list):
    players= set()
    for row in list:
        for column  in row:
            LogSearch = re.search(r'Log[A-Z]',column)
            players.add(LogSearch.group(0)[-1:])
    return players


def add_restrictions_and_generate_tamarin_code_for_this_group(group_action_labels,freshRL,groupname):
    copyfile("finaleach.txt","tempfinal.txt")
    # construct and add restrictions
    add_uniqueness_restrictions_to_tamarin_file("tempfinal.txt", freshRL, group_action_labels)
    # construct and add restrictions
    add_correspondence_restrictions_to_tamarin_file("tempfinal.txt", group_action_labels)
    # if output file already exists, remove it and rename final output as tamatinstcheck.spthy
    stealth_output_file_name = "stcheck_on_logs_of_" + groupname + "_in" + os.path.basename(input_file)
    if Path(stealth_output_file_name).is_file():
        os.remove(stealth_output_file_name)
        os.rename("tempfinal.txt", stealth_output_file_name)
    else:    # if output file does not  exist,  rename final output as tamatinstcheck.spthy
        os.rename("tempfinal.txt", stealth_output_file_name)


# Returns logs of only one participant
def return_player_action_labels(list,player):
    player_allist= [[]]
    idx = -1
    for row in list:
        idx += 1
        for column  in row:
            player_allist.append([])
            LogSearch = re.search(r'Log[A-Z]',column)
            if (player == LogSearch.group(0)[-1:] or   LogSearch.group(0)[-1:]=='X'):
                player_allist[idx].append(column)

    # Remove blank lists
    final_player_allist = [x for x in player_allist if x != []]

    return final_player_allist

# Returns logs of only one participant
def return_group_player_action_labels(list,players):
    player_allist= [[]]
    idx = -1
    for row in list:
        idx += 1
        for column  in row:
            player_allist.append([])
            LogSearch = re.search(r'Log[A-Z]',column)
            if (LogSearch.group(0)[-1:] in players):
                player_allist[idx].append(column)

    # Remove blank lists
    final_player_allist = [x for x in player_allist if x != []]

    return final_player_allist

# Returns all possible combinations of participants
def powersetOfParticipants(partners):
    """
    Returns all the subsets of this set. This is a generator.
    """
    if len(partners) <= 1:
        yield partners
        yield []
    else:
        for item in powersetOfParticipants(partners[1:]):
            yield [partners[0]]+item
            yield item
# Accept tamarin file , modify the rules and check for stealthiness

# Formats source file by removing all one-line comments and removing whitespaces from  rules
# to bring all rules / lemmas /restrictions etc in one line for further processing

input_file=sys.argv[1]
# For one file, uncomment the following line and provide relative path
#input_file="PartnerNames/NSPK3.spthy"
clean_tamarin_file(input_file)
format_tamarin_file("temp.txt")
remove_multiline_comments_from_rules("ready.txt")
remove_multiline_comments_from_lemma("ready.txt")

## Uncomment the following lines if want to check the numbered action labels before adding sid
#unique_numbered_action_label_names= numbered_action_labels("ready.txt")
# print(unique_numbered_action_label_names)
# Adds newlines before rule, lemma and restriction for further processing
add_newline_before_rule("ready.txt")
add_newline_before_lemmas("ready.txt")
add_newline_before_restrictions("ready.txt")


## Collect fresh name into a dictionary
freshList={}
freshListFinal=Collect_fresh_from_premise("ready.txt",freshList)

#print(freshListFinal)


Add_session_id_to_premise("ready.txt", "Fr(~sid)", "In(sid)")
Add_session_id_to_first_conclusion("ready.txt", "Out(~sid)")
Add_session_id_to_Stealth_Logs('final.txt')

copyfile("final.txt","finaleach.txt")
# # File final.txt is ready for processing
get_rulewise_action_labels = [[]]
#
received_rulewise_action_labels = Split_action_labels("final.txt", get_rulewise_action_labels)
#print(received_rulewise_action_labels)
#Extract only Log action labels from received_rulewise_action_labels and construct restrictions on them
# ## Collect unique action label names
## Uncomment the following lines if want to check the numbered action labels after  adding sid
unique_numbered_action_label_names = numbered_action_labels("final.txt")
#print(unique_numbered_action_label_names)
all_action_label_names = complete_list__action_labels("final.txt")
#print(unique_numbered_action_label_names)
non_numbered_action_labels = all_action_label_names.difference(unique_numbered_action_label_names)
#print(unique_numbered_action_label_names)
#

#Remove all blank lists from received rulewise action labels and
# select only Log labels for further processing and remove empty lists fpr correspondence restrictions
final_received_rulewise_action_labels = select_Log_labels(received_rulewise_action_labels)
#print(final_received_rulewise_action_labels)


# Find all the participants
players=return_players(final_received_rulewise_action_labels)


l = list(players)
all_groupings_players = [x for x in powersetOfParticipants(l) if x]
# Add restrictions and generate tamarin source code for  stealth check based on  all possible groupings of participants logs
#print(all_groupings_players)
this_group_action_label=[[]]
for groups in all_groupings_players:
    this_group_action_label.append([])
    this_group_action_label=return_group_player_action_labels(final_received_rulewise_action_labels,groups)
    add_restrictions_and_generate_tamarin_code_for_this_group(this_group_action_label,freshListFinal,"_and_".join(groups))



os.remove("ready.txt")
os.remove("temp.txt")
os.remove("final.txt")
os.remove("finaleach.txt")
