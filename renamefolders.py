import sys
import os
import re
import zipfile
import shutil

#Flag constants
ZIP_FLAGS = ['-z', '-zip', '-unzip']
STUDENTS_FLAGS = ['-s', '-students']
FLATTEN_FLAGS = ['-f', '-flatten']
EXTERNAL_FILE_FLAGS = ['-e', '-external']
SHORTEN_EXTENSION_FLAGS = ['-x', '-extension', '-short', '-shorten']
PROTECT_PREFIX_FLAGS = ['-p', '-protect', '-prefix']
VERBOSE_FLAGS = ['-v', '-verbose']
HELP_FLAGS = ['-h', '-help']

#Other constants
COMMENT = '#'
SPACE = '~'
IGNORE = set([".", "__"])
SEP = "_"

#Helper function for displaying text that doesn't wrap lines
#in the Command Prompt
#Assumes tabs are width 8 and there are 80 columns
def display_format(strg, width = 80, twidth = 8):
    #Split the string into words
    split_strg = strg.split()
    #Technical thing that helps with boundary conditions
    split_strg.append("")
    #Build a new string with line breaks/tabs
    new_strg = "\t\t"
    #At start, we're two tabs in
    new_len = 2 * twidth
    #Loop through the words
    for i in range(len(split_strg) - 1):
        #Append the next word
        new_strg += split_strg[i]
        #Update the length of the current line
        new_len += len(split_strg[i]) + 1
        #Check if next word would "wrap"
        if new_len + len(split_strg[i + 1]) >= width:
            #It would, so make a new line
            new_strg += "\n\t\t"
            new_len = 2 * twidth
        else:
            #It wouldn't, so make a space
            new_strg += " "
    #Return the new, formatted string
    return new_strg

#Display the help info for the program
#Usage and details
def display_help():
    print()
    print("USAGE: python3 renamefolders.py directory [options]")
    print()
    print("\tdirectory:\n%s"%display_format("The directory to process"))
    print()
    print("OPTIONS:")
    external_string = EXTERNAL_FILE_FLAGS[0] + " (" +\
        ', '.join(EXTERNAL_FILE_FLAGS[1:]) + ") external_file"
    print("\t%s\n%s"%(external_string, display_format(
        "If given, copy the file "
        "specified by external_file into the folder of submissions. "
        "Useful if, e.g., you provided a module for them to use, and "
        "their submitted code all imports your module. "
        "Can be passed multiple times; each flag takes "
        "only one argument.")))
    print()
    flatten_string = FLATTEN_FLAGS[0] + " (" +\
        ', '.join(FLATTEN_FLAGS[1:]) + ")"
    print("\t%s\n%s"%(flatten_string, display_format("If given, "
        "remove the folder structure and put all submissions in a "
        "single folder.")))
    print()
    student_string = STUDENTS_FLAGS[0] + " (" +\
        ', '.join(STUDENTS_FLAGS[1:]) + ") students_file"
    print("\t%s\n%s"%(student_string, display_format("If given, "
        "use a file to ensure student names are treated accurately. "
        "Can only be provided once.")))
    print()
    shorten_string = SHORTEN_EXTENSION_FLAGS[0] + " (" +\
        ', '.join(SHORTEN_EXTENSION_FLAGS[1:]) + ") file_extension_string"
    print("\t%s\n%s"%(shorten_string, display_format("If given, "
        "files with the specified extension, e,g \".py\", are given "
        "short names, typically just the surname of the student who "
        "submitted them. Can be passed multiple times; each flag takes "
        "only one argument. The -p flag can be used to gain further "
        "control over this process.")))
    print()
    protect_string = PROTECT_PREFIX_FLAGS[0] + " (" +\
        ', '.join(PROTECT_PREFIX_FLAGS[1:]) + ") prefix_string"
    print("\t%s\n%s"%(protect_string, display_format("If given, "
        "files with the specified prefix, e,g \"aa\", are NOT given "
        "short names, even if the -e flag would apply. Use if, e.g., "
        "students are likely to submit files you provided them, and "
        "you don't want to rename those. "
        "Can be passed multiple times; each flag takes "
        "only one argument.")))
    print()
    zip_string = ZIP_FLAGS[0] + " (" + ', '.join(ZIP_FLAGS[1:]) + ")"
    print("\t%s\n%s"%(zip_string, display_format("If given, extract "
        "files from ZIP submissions")))
    print()
    verbose_string = VERBOSE_FLAGS[0] + " (" +\
        ', '.join(VERBOSE_FLAGS[1:]) + ")"
    print("\t%s\n%s"%(verbose_string, display_format("If given, "
        "produce verbose output.")))
    print()
    help_string = HELP_FLAGS[0] + " (" +\
        ', '.join(HELP_FLAGS[1:]) + ")"
    print("\t%s\n%s"%(help_string, display_format("If given, display "
        "this help page and exit.")))
    print()

#Class encapsulating a student
class Student:
    #Constructor
    #A student has a first name, a last name, and a nickname
    def __init__(self, first, last, nickname):
        self.first = first.replace(SPACE, " ")
        self.last = last.replace(SPACE, " ")
        self.nickname = nickname.replace(SPACE, " ")
        self.folder = None

    #Check if this student has already been assigned a folder
    def has_folder(self):
        return self.folder is not None

    #Assign this student a folder
    def assign_folder(self, folder):
        self.folder = folder

    #Get the student's folder
    def get_folder(self):
        return self.folder

    #For nice printing
    def get_student_name(self):
        if self.nickname == self.first:
            return "%s %s"%(self.first, self.last)
        else:
            return "%s (%s) %s"%(self.first, self.nickname, self.last)

    #String for identifying students
    def get_id_string(self, number = 0):
        if number == 0:
            return ("%s  %s"%(self.last, self.first)).replace(" ", SEP)
        else:
            return ("%s  %s%d"%(self.last, self.first, number)).replace(" ", SEP)

    #str
    def __str__(self):
        return self.get_id_string()

#Import a list of students from a file
#File should have each student on one line
#Format is firstname [space] lastname
#If the name (first or last) contains spaces, use ~ instead of spaces
#Empty lines or lines starting with # are ignored
#You may also specify a nickname between the first and last name
#in parentheses, e.g. Abigail (Abby) Bryan
#If you have multiple students with the same name that gets
#tokenized different ways, e.g. Cole Spencer Evans (one's last
#name is Spencer Evans; the other's is Evans), you're out of luck
#for sorting them properly.  Sorry.
def import_students_from_file(student_file):
    #Initialize an empty dictionary of students
    students = dict()
    #Open the file
    with open(student_file, 'r') as sfd:
        #Loop through the lines of the file
        for line in sfd:
            #Remove whitespace
            ls = line.strip()
            #Extract first and last names
            line2 = ls.split()
            #Get the nickname, if there is one
            if len(line2) == 3:
                #There is one
                nickname = line2[1]
                #Make sure it's in parentheses
                if nickname[0] != '(' or nickname[-1] != ')':
                    #It's not
                    raise ValueError("Invalid nickname specification: "
                        "%s"%line)
                else:
                    #Remove the parentheses
                    nickname = nickname[1:-1]
                    #Remove the nickname from the list
                    del line2[1]
            else:
                #No nickname, just use first name
                nickname = line2[0]
            #Check if we should ignore the current line
            if len(ls) == 0 or ls[0] == COMMENT:
                continue
            #Make sure we have exactly two tokens
            elif len(line2) != 2:
                raise ValueError("Wrong number of tokens found for "
                    "student: %s"%line)
            #Append the student to the list of students
            student = Student(line2[0], line2[1], nickname)
            #This loop handles multiple students with same name
            i = 0
            while True:
                if "%s%d"%(str(student), i) not in students:
                    students["%s%d"%(str(student), i)] = student
                    break
                else:
                    i += 1
    #Return the student list
    return students

#Given a directory, unzip all ZIP files in that directory
#and extract to that directory
def unzip_zips(dirc, verbose = False):
    #Remember the current working directory
    cur_wd = os.getcwd()
    #Change working directory to the one we care about
    os.chdir(dirc)
    #Look for ZIP files
    if verbose:
        print("Looking for ZIP files in %s"%dirc)
    dircs = set()
    zips = []
    for itm in os.scandir(dirc):
        if itm.is_file() and len(itm.name) >= 4 and\
                itm.name[-4:] in {'.ZIP', '.zip'}:
            #We found one!
            if verbose:
                print("Found ZIP: %s"%itm.name)
            zips.append(itm.name)
        elif itm.is_dir():
            #Keep track of what directories were already there
            dircs.add(itm.name)
    #Extract the ZIPs and delete them
    for zip in zips:
        #Do the extract
        with zipfile.ZipFile(zip, 'r') as z:
            z.extractall()
        if verbose:
            print("Extract successful")
        os.remove(zip)
        if verbose:
            print("Deleted file %s"%zip)
    #Look for new directories and flatten them out
    if verbose:
        print("Looking for directories created by unzip")
    new_dircs = []
    for itm in os.scandir(dirc):
        if itm.is_dir() and itm.name not in dircs:
            #We found a new directory
            if verbose:
                print("New directory found: %s"%itm.name)
            new_dircs.append(itm.name)
    for new_dirc in new_dircs:
        #Extract the files from it, if relevant
        #Ignore if starts with . or __
        ignore = False
        for ig in IGNORE:
            if new_dirc[:len(ig)] == ig:
                ignore = True
                break
        if ignore:
            #Delete the whole thing
            shutil.rmtree(new_dirc)
            if verbose:
                print("Deleted irrelevant directory: %s"%new_dirc)
        else:
            move_files = []
            for in_itm in os.scandir(new_dirc):
                #Tag file for moving
                move_files.append(in_itm)
                if verbose:
                    print("File/directory %s tagged for moving"%in_itm.name)
            for move_file in move_files:
                #Move the file
                os.rename(move_file.path, move_file.name)
                if verbose:
                    print("Renamed file/directory %s to %s"%\
                        (move_file.path, move_file.name))
            #Remove the directory
            os.rmdir(new_dirc)
            if verbose:
                print("Removed directory %s"%new_dirc)
    #Done. Go back to the old working directory
    if verbose:
        print("Done looking for ZIP files")
    os.chdir(cur_wd)

if __name__ == '__main__':
    ##Make sure there's a folder specified
    if len(sys.argv) < 2:
        display_help()
        sys.exit(0)
    #Get the folder
    folder = sys.argv[1]
    #Make sure the folder is valid
    if not os.path.isdir(folder):
        print('Error: directory specified is not a valid directory')
        sys.exit(0)
    #Remove os.sep from end of folder, if it's there
    if folder[-1] == os.sep:
        folder = folder[:-1]
    #Make folder absolute, if it's relative
    folder = os.path.abspath(folder)

    ##Default values of other things
    #Should we unzip ZIP files?
    unzip = False
    #Do we have a list of students to cross-reference?
    students = None
    #Should we eliminate the folder structure?
    flatten = False
    #What external files should we bring into the folder?
    files = set()
    #Are there any extensions where we should just make the
    #file name be the student's last name?
    shorten_extensions = set()
    #Given extensions to shorten, are there any prefixes to filenames
    #with those extensions that indicate we actually don't want
    #to shorten those particular file names?
    protected_prefixes = set()
    #Should we print a bunch of stuff while this is running?
    verbose = False

    ##Process the rest of the arguments
    i = 2
    while i < len(sys.argv):
        #Get the current flag
        flag = sys.argv[i]
        #Figure out what to do
        if flag in ZIP_FLAGS:
            #We should unzip ZIP files
            unzip = True
            #Advance i by 1
            i += 1
        elif flag in STUDENTS_FLAGS:
            #We are using a list of students
            if students is not None:
                #This is the second time a student file has been specified
                #Only one student file should exist
                print("Error: Multiple student files specified")
                sys.exit(0)
            elif i + 1 == len(sys.argv):
                #The student flag was the last thing in the command,
                #meaning no file was specified
                print("Error: Student file flag used without file specified")
                sys.exit(0)
            else:
                #Get the file
                student_file = sys.argv[i+1]
                if os.path.isfile(student_file):
                    #The file exists
                    #Get the list of students
                    try:
                        students = import_students_from_file(student_file)
                    except ValueError as e:
                        #The student file was invalid
                        print(e.args[0])
                        sys.exit(0)
                    #Advance i by 2
                    i += 2
                else:
                    #File specfied doesn't exist
                    print("Error: Student file not found: %s"%student_file)
                    sys.exit(0)
        elif flag in FLATTEN_FLAGS:
            #We should flatten the folder structure
            flatten = True
            #Advance i by 1
            i += 1
        elif flag in EXTERNAL_FILE_FLAGS:
            #Bring in an external file
            if i + 1 == len(sys.argv):
                #The external file flag was the last thing in the command,
                #meaning no file was specified
                print("Error: External file flag used without file specified")
                sys.exit(0)
            else:
                #Get the file
                external_file = sys.argv[i+1]
                if os.path.isfile(external_file):
                    #The file exists
                    #Add it to the list of external files to bring in
                    files.add(external_file)
                    #Advance i by 2
                    i += 2
                else:
                    #File specfied doesn't exist
                    print("Error: External file not found: %s"%external_file)
                    sys.exit(0)
        elif flag in SHORTEN_EXTENSION_FLAGS:
            #Extension specified to shorten
            if i + 1 == len(sys.argv):
                #The shorten extension flag was the last thing in the command,
                #meaning no extension was specified
                print("Error: Shorten extension flag used without "
                    "extension specified")
                sys.exit(0)
            else:
                #Get the extension and add it to the list of extensions
                #to shorten
                shorten_extensions.add(sys.argv[i+1])
                #Advance i by 2
                i += 2
        elif flag in PROTECT_PREFIX_FLAGS:
            #Prefix specified to protect
            if i + 1 == len(sys.argv):
                #The protect prefix flag was the last thing in the command,
                #meaning no prefix was specified
                print("Error: Protect prefix flag used without "
                    "prefix specified")
                sys.exit(0)
            else:
                #Get the prefix and add it to the list of prefixes to protect
                protected_prefixes.add(sys.argv[i+1])
                #Advance i by 2
                i += 2
        elif flag in VERBOSE_FLAGS:
            #We should print things
            verbose = True
            #Advance i by 1
            i += 1
        elif flag in HELP_FLAGS:
            #We should display the help instead of doing anything else
            display_help()
            sys.exit(0)
        else:
            print("Invalid flag: "%flag)
            print()
            display_help()
            sys.exit(0)

    #Moodle folder regex
    moodle_regex = re.compile("^\S* .*_\d*_assignsubmission_file_$")
    renamed_regex = re.compile("^\S*_\S*$")

    #Get the list of folders
    dirs = []
    dnames = set()
    s_list = []
    #Scan the specified folder for directories
    if verbose:
        print("Scanning for Moodle download folders")
    for itm in os.scandir(folder):
        #Check if we're looking at a directory
        if itm.is_dir():
            #Yes
            #Now, check if it's a directory from Moodle
            if moodle_regex.match(itm.name):
                #It is
                if verbose:
                    print("Found yet to be processed folder %s"%itm.name)
                #Get the tokens before the first underscore
                #and get the part after the underscore
                uindex = itm.name.find(SEP)
                sname = itm.name[:uindex].split()
                #Figure out the corresponding student
                if students is None:
                    #Make one up
                    #Assume first name is one word
                    first = sname[0]
                    last = SPACE.join(sname[1:])
                    student = Student(first, last, first)
                    student_num = 0
                    while student.get_id_string(student_num) in dnames:
                        #Need to increase student_num
                        student_num += 1
                else:
                    #Check all possible parsings of the student's name
                    student = None
                    for split_loc in range(1, len(sname)):
                        #Try a name
                        try_student = Student(SPACE.join(sname[:split_loc]),\
                            SPACE.join(sname[split_loc:]),\
                            SPACE.join(sname[:split_loc]))
                        done_trying = False
                        #Loop in case there are multiple students
                        #with the same name
                        i = 0
                        while True:
                            #Does the student associated with this folder
                            #actually exist?
                            if "%s%d"%(str(try_student), i) not in students:
                                break
                            #Given yes, is it a duplicate that we've already
                            #assigned before
                            elif students["%s%d"%(str(try_student), i)].\
                                    has_folder():
                                i += 1
                            #Ok, we're good to assign the folder
                            else:
                                student = students["%s%d"%(str(try_student),\
                                    i)]
                                student_num = i
                                if verbose:
                                    print("Folder belongs to student %s"%\
                                        student.get_student_name())
                                done_trying = True
                                break
                        if done_trying:
                            break
                    if student is None:
                        #We failed to find a student
                        print("Error: folder %s has no "
                            "corresponding student"%itm.name)
                        sys.exit(0)
                #Keep track of the directory's name and its future name
                new_name = student.get_id_string(student_num)
                dirs.append((itm.name, new_name))
                dnames.add(new_name)
                student.assign_folder(new_name)
                #Remember this student
                s_list.append([student, student_num])
                if verbose:
                    print("Matching student %s to folder %s with number %d"%\
                        (str(student), student.get_folder(), student_num))
                #Unzip, if we want to do that
                if unzip:
                    unzip_zips(folder + os.sep + itm.name, verbose)
            #Next, check if it's already been renamed by our program
            elif renamed_regex.match(itm.name):
                #It is
                if verbose:
                    print("Found already renamed folder %s"%itm.name)
                sname = itm.name.split(SEP + SEP)
                #Make up a student
                first = sname[1]
                #remove numbers from end of first
                while ord(first[-1]) >= ord('0') and\
                        ord(first[-1]) <= ord('9'):
                    first = first[:-1]
                #Student's number
                student_num = 0
                if first != sname[1]:
                    student_num = int(sname[1][len(first):])
                #Last name
                last = sname[0]
                try_student = Student(first, last, first)
                #Figure out the corresponding student
                if students is None:
                    #Make one up
                    student = try_student
                elif itm.name + '0' in students:
                    #Default student, no repeatss
                    student = students[itm.name + '0']
                elif itm.name not in students:
                    print("Error: folder %s has no "
                        "corresponding student"%itm.name)
                    sys.exit(0)
                else:
                    student = students[itm.name]
                #Keep track of the directory's name
                dnames.add(itm.name)
                student.assign_folder(itm.name)
                #Remember this student
                s_list.append([student, student_num])
                if verbose:
                    print("Matching student %s to folder %s with number %d"%\
                        (str(student), student.get_folder(), student_num))
                #Unzip, if we want to do that
                if unzip:
                    unzip_zips(folder + os.sep + itm.name, verbose)
    #Rename the folders
    if verbose:
        print()
        print("Renaming folders")
    #Loop through the directories needing renaming
    for dirc in dirs:
        #Do the renaming
        os.rename(folder + os.sep + dirc[0], folder + os.sep + dirc[1])
        if verbose:
            print("Renamed %s to %s"%(dirc[0], dirc[1]))
    if verbose:
        print("Done renaming")

    #Folders prefixes
    if flatten and len(shorten_extensions) > 0:
        if verbose:
            print()
            print("Figuring out shortened names")
        #List the folders
        folder_list = [sn[0].get_folder() for sn in s_list]
        #Sort the list of folders
        folder_list.sort()
        #Look for optimal prefixes
        folder_prefixes = dict()
        lnames = dict()
        #First, group everybody by last name
        i = 0
        while i < len(folder_list):
            fldr = folder_list[i]
            #Look for people with the SAME name
            j = i + 1
            while j < len(folder_list) and\
                    folder_list[j][:len(fldr)] == fldr:
                j += 1
            #Figure out the current last name
            lname = fldr[:folder_list[i].find(SEP)]
            if lname not in lnames:
                lnames[lname] = []
            #Create an entry, keeping track of the number of people
            #with that name
            lnames[lname].append((fldr, j - i))
            if verbose:
                print("Name %s; last name %s; %d people"%(fldr, lname, j - i))
            #Advance to the next unique name
            i = j
        #Now, go through and find unique prefixes
        for lname in lnames:
            if verbose:
                print("Now considering last name %s"%lname)
            #Loop through the names with that last name
            for i in range(len(lnames[lname])):
                #Get the folder name and count,
                #and the index after the last name
                fldr = lnames[lname][i][0]
                ct = lnames[lname][i][1]
                idx = fldr.find(SEP)
                #Extend the prefix until it's unique
                while True:
                    ok = True
                    #What's the current prefix?
                    name = fldr[:idx]
                    #Check to see if it's unique?
                    for j in range(len(lnames[lname])):
                        if i != j and lnames[lname][j][0][:idx] == name:
                            #It's not
                            ok = False
                            break
                    if ok:
                        if verbose:
                            print("Found unique prefix %s"%name)
                        #Prefix was unique
                        #Let's roll with it
                        folder_prefixes[fldr] = name
                        #In case there were multiple people with the same name
                        #Need to account for all of them
                        for j in range(1, ct):
                            folder_prefixes[fldr + str(j)] = name + str(j)
                        if verbose:
                            print("Updated %d entries"%ct)
                        break
                    else:
                        #Try again with a longer prefix
                        idx += 1
        #Remove underscores from shortened names
        for fldr in folder_prefixes:
            folder_prefixes[fldr] = folder_prefixes[fldr].replace(SEP, "")
            if verbose:
                print("Prefix for %s changed to %s"%(fldr,\
                    folder_prefixes[fldr]))

    #Flatten/Shorten/Exemption
    #This works even if you've already done the rest
    if flatten:
        if verbose:
            print()
            print("Flattening")
        for student_and_num in s_list:
            student = student_and_num[0]
            student_num = student_and_num[1]
            #Get the student's folder
            s_folder = student.get_folder()
            #Files to move
            move_files = []
            for in_itm in os.scandir(folder + os.sep + s_folder):
                #Tag file for moving
                move_files.append(in_itm)
                if verbose:
                    print("File/directory %s tagged for moving"%in_itm.name)
            for move_file in move_files:
                #Make the new name
                if student_num == 0:
                    new_name = s_folder + SEP + move_file.name
                else:
                    new_name = student.last.replace(" ", SEP) +\
                        str(student_num) + SEP + SEP +\
                        student.first.replace(" ", SEP) + SEP + move_file.name
                #Check if need to shorten filename
                for ext in shorten_extensions:
                    if move_file.name[-len(ext):] == ext:
                        if verbose:
                            print("File %s has extension %s"%\
                                (move_file.name, ext))
                        #We've matched an extension to shorten
                        #Check if we need to actually not shorten it
                        protected = False
                        for pre in protected_prefixes:
                            if move_file.name[:len(pre)] == pre:
                                #We actually need to not shorten it
                                protected = True
                                if verbose:
                                    print("File %s has protected prefix %s"%\
                                        (move_file.name, pre))
                                break
                        if not protected:
                            #Do the rename
                            #Use the prefix created earlier
                            new_name = folder_prefixes[s_folder] + ext
                            if verbose:
                                print("File %s tagged for renaming to %s"%\
                                    (move_file.name, new_name))
                        break
                #Check if the file already exists
                if os.path.isfile(folder + os.sep + new_name):
                    if verbose:
                        print("File %s already exists"%new_name)
                    #Append a number to make it not already exist
                    dot_index = new_name.rfind(".")
                    #If there is no dot, we'll add numbers to the end
                    if dot_index == -1:
                        dot_index = len(new_name)
                    #Ignore files that start with dot
                    if dot_index != 0:
                        #Loop until we find an available name
                        i = 0
                        while os.path.isfile(folder + os.sep +\
                                new_name[:dot_index] + SEP + str(i) +\
                                new_name[dot_index:]):
                            i += 1
                        #Use the available name
                        new_name = new_name[:dot_index] + SEP + str(i) +\
                            new_name[dot_index:]
                        if verbose:
                            print("Instead using name %s"%new_name)
                #Check if we should ignore the file
                ignore = False
                for ig in IGNORE:
                    if move_file.name[:len(ig)] == ig:
                        ignore = True
                        break
                if ignore:
                    #Delete the thing
                    if os.path.isfile(folder + os.sep + s_folder + os.sep +\
                            move_file.name):
                        os.remove(folder + os.sep + s_folder + os.sep +\
                            move_file.name)
                        if verbose:
                            print("Deleted irrelevant file: %s"%move_file.name)
                    else:
                        shutil.rmtree(folder + os.sep + s_folder + os.sep +\
                            move_file.name)
                        if verbose:
                            print("Deleted irrelevant directory: %s"%new_dirc)
                else:
                    #Prepare to move
                    new_name = folder + os.sep + new_name
                    #Move the file
                    os.rename(folder + os.sep + s_folder + os.sep +\
                        move_file.name, new_name)
                    if verbose:
                        print("Renamed file/directory %s to %s"%\
                            (folder + os.sep + s_folder + os.sep +\
                            move_file.name, new_name))
            #Remove the directory
            shutil.rmtree(folder + os.sep + s_folder)
            if verbose:
                print("Removed directory %s"%s_folder)

    #Bring in external files
    if len(files) > 0 and verbose:
        print()
        print("Bringing in external files")
    for external in files:
        #Copy in the file
        shutil.copy2(external, folder)
        if verbose:
            print("Copied in file %s"%external)

    if verbose:
        print()
        print("Done!")
