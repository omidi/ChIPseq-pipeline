#!/usr/bin/env python
import component_skeleton.main
import subprocess
import re, os
from string import *

def execute(cf):
    FMIid = cf.get_parameter("FMIid", "string")
    out_log = cf.get_output("numberMappableReads_log")
    annoType = cf.get_parameter("annoType", "string")
    FMIpath = cf.get_parameter("FMIpath", "string")
    perlPATH = cf.get_parameter("perlPATH", "string")
    FMI_output_dir = cf.get_parameter("FMI_output_dir", "string")

    #to be sure to use the right perl
    os.environ['PATH'] =  perlPATH + ':' + os.environ['PATH']

    command1 = ' '.join([perlPATH,
                         FMIpath+'/soft/extractData.pl -f',
                         FMIid,
                         annoType,
                        'genome',
                         FMI_output_dir])
    
    command2 = ' '.join([perlPATH,
                        FMIpath+'/soft.bc2/frag2totalGenomic.pl - >',
                        out_log])

    p1 = subprocess.Popen(command1,
                          stdout=subprocess.PIPE,
                          shell=True)

    p2 = subprocess.Popen(command2,
                          stdin=p1.stdout,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          shell=True)

    p1.stdout.close()
    stdout_value, stderr_value = p2.communicate()

    print 'p2 returncode', p2.returncode, p2.poll()
    print 'p1 returncode', p1.returncode, p1.poll()

    print stdout_value
    print stderr_value

    if p2.poll() > 0:
        print 'p2 failed'
        return -1
    if p1.poll() > 0:
        print 'p1 failed'
        return -1


    return 0


component_skeleton.main.main(execute)
