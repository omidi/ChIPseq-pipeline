#!/import/bc2/home/nimwegen/GROUP/local/bin/python
#/usr/bin/env python

import sys, os
import yaml
from string import *
import argparse
import subprocess
import smtplib
from email.mime.text import MIMEText

def extractFileType(f):

    t = None

    if f.endswith('.fastq.gz'):
        t = 'fastq'
    elif f.endswith('.fastq'):
        t = 'fastq'
    elif f.endswith('.fq.gz'):
        t = 'fastq'
    elif f.endswith('fq'):
        t = 'fastq'
    elif f.endswith('.fasta.gz'):
        t = 'fasta'
    elif f.endswith('.fasta'):
        t = 'fasta'
    elif f.endswith('.fa.gz'):
        t = 'fasta'
    elif f.endswith('.fa'):
        t = 'fasta'
    elif f.endswith('.bed.gz'):
        t = 'bed'
    elif f.endswith('.bed'):
        t = 'bed'

    return t


def main():

    parser = argparse.ArgumentParser(description='Run pipe-line.')
    parser.add_argument('-fg', dest='fg', action='store', required=True, help='Space separated string of foreground files')
    parser.add_argument('-bg', dest='bg', action='store', required=True, help='Space separated string of foreground files')
    parser.add_argument('-wm', dest='WM', action='store', required=False, help='Path to a WM')
    parser.add_argument('-a3', dest='adaptor', action='store', required=False, help='3\' adaptor sequence')
    parser.add_argument('-g', dest='genome', action='store', required=True, help='genome')
    parser.add_argument('-fgwin', dest='fg_win', action='store', required=True, help='FG window size')
    parser.add_argument('-bgwin', dest='bg_win', action='store', required=True, help='BG window size')
    parser.add_argument('-step', dest='step_win', action='store', required=True, help='window step size')
    parser.add_argument('-mf', dest='motiffinding', action='store', required=True, help='motif finding yes or no (1 or 0)')
    parser.add_argument('-fdr', dest='fdr', action='store', required=True, help='False discovery rate used for peak calling')
    parser.add_argument('-email', dest='user_email', action='store', required=False, help='e-mail address of the user')

    args = parser.parse_args()

    scripts_dir = os.path.split(os.path.realpath(__file__))[0]
    templates_path = os.path.join(os.path.split(scripts_dir)[0], 'templates')
    configuration_path = os.path.join(os.path.split(scripts_dir)[0], 'config')

    params_template = os.path.join(configuration_path, 'params_%s.yaml' %(args.genome))

    # load yaml template
    cf = open(params_template)
    params = yaml.load(cf)

    # given on web site:
    fg_files = args.fg.split()
    bg_files = args.bg.split()

    if args.motiffinding == '1':
        params['DO_MOTIF_FINDING'] = True
    else:
        params['DO_MOTIF_FINDING'] = False

    try:
        WM = args.wm
    except AttributeError:
        WM = False
    try:
        adaptor = args.adaptor
    except AttributeError:
        adaptor = False

    for f in fg_files:
        t = extractFileType(f)

        if t == 'fastq':
            try:
                params['IP_FASTQ_FILES']['IP'] += f + ' '
            except TypeError:
                params['IP_FASTQ_FILES'] = {}
                params['IP_FASTQ_FILES']['IP'] = f + ' '
        if t == 'fasta':
            try:
                params['IP_FASTA_FILES']['IP'] += f + ' '
            except TypeError:
                params['IP_FASTA_FILES'] = {}
                params['IP_FASTA_FILES']['IP'] = f + ' '
        if t == 'bed':
            try:
                params['IP_BED_FILES']['IP'] += f + ' '
            except TypeError:
                params['IP_BED_FILES'] = {}
                params['IP_BED_FILES']['IP'] = f + ' '

    for f in bg_files:
        t = extractFileType(f)

        if t == 'fastq':
            try:
                params['BG_FASTQ_FILES'] += f + ' '
            except TypeError:
                params['BG_FASTQ_FILES'] = f + ' '
        if t == 'fasta':
            try:
                params['BG_FASTA_FILES'] += f + ' '
            except TypeError:
                params['BG_FASTA_FILES'] = f + ' '
        if t == 'bed':
            try:
                params['BG_BED_FILES'] += f + ' '
            except TypeError:
                params['BG_BED_FILES'] = f + ' '

    if WM:
        params['WM'] = {}
        params['WM']['IP'] = WM

    if adaptor:
        params['ADAPTOR'] = adaptor

    params['FDR'] = args.fdr
    params['WINDOW'] = args.fg_win
    params['BACKGROUND_WINDOW'] = args.bg_win
    params['STEP'] = args.step_win

    o = open('p.yaml', 'w')
    o.write(yaml.dump(params))
    o.close()

    # email stuff:
    s = smtplib.SMTP('localhost')
    me = 'severin.berger@stud.unibas.ch'
    you = 'severin.berger@stud.unibas.ch'
    msg = MIMEText('User e-mail address: %s\nWorking Directory: %s\nGiven parameters: %s\n' %(args.user_email, os.getcwd(), args))
    msg['From'] = me
    msg['To'] = you

    try:
        msg['Subject'] = 'CRUNCH data submitted'
        s.sendmail(me, [you], msg.as_string())
        s.quit()
    except Exception, e:
        print 'email send failed:'
        print e
        pass


    print 'Setting up CRUNCH:'
    proc = subprocess.Popen('%s/run_Pipeline.py p.yaml' %(scripts_dir),
                            stdout=subprocess.PIPE,
                            stderr= subprocess.PIPE,
                            shell=True)

    stdout_value, stderr_value = proc.communicate()

    if proc.poll() > 0:
        print stdout_value
        print stderr_value
        print 'CRUNCH set up failed:\n'

        s = smtplib.SMTP('localhost')
        msg = MIMEText('Working Directory: %s\nUser e-mail address: %s' %(os.getcwd(), args.user_email))
        msg['From'] = me
        msg['To'] = you
        msg['Subject'] = 'CRUNCH set up failed'
        s.sendmail(me, [you], msg.as_string())
        s.quit()

        sys.exit(1)
    else:
        print 'CRUNCH set up successfully.\n'



    cs = open('andurilCOMMAND').readlines()
    sourceC = cs[1].strip()
    andurilC = cs[3].strip()

    # load environment variables
    crunch_env = os.path.join(configuration_path, 'crunch.env')
    env_dict = {}
    for line in open(crunch_env):
        if line.strip() and not line.startswith('#'):
            t = line.strip().split()[1].split('=')
            env_dict[t[0]] = t[1]

    print env_dict

    print andurilC

    # Run CRUNCH
    print 'Running CRUNCH:'
    proc = subprocess.Popen(andurilC + ' > crunch_log', 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True,
                            env=env_dict)

    stdout_value, stderr_value = proc.communicate()

    if proc.poll() > 0:
        print 'Pipe-line failed:\n'
        print stderr_value
        print stdout_value
        os.system('grep ERROR crunch_log')

        s = smtplib.SMTP('localhost')
        msg = MIMEText('Working Directory: %s\nUser e-mail address: %s' %(os.getcwd(), args.user_email))
        msg['From'] = me
        msg['To'] = you
        msg['Subject'] = 'CRUNCH execution failed'
        s.sendmail(me, [you], msg.as_string())
        s.quit()

        sys.exit(1)
    else:
        print 'Pipe-Line ran successfully.\n'


    # Create Report
    print 'Create CRUNCH report:'
    proc = subprocess.Popen('%s/make_output.py p.yaml' %(scripts_dir),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True,
                            env=env_dict)

    stdout_value, stderr_value = proc.communicate()

    if proc.poll() > 0:
        print 'CRUNCH report creation failed:\n'
        print stdout_value
        print stderr_value

        s = smtplib.SMTP('localhost')
        msg = MIMEText('Working Directory: %s\nUser e-mail address: %s' %(os.getcwd(), args.user_email))
        msg['From'] = me
        msg['To'] = you
        msg['Subject'] = 'CRUNCH report creation failed'
        s.sendmail(me, [you], msg.as_string())
        s.quit()

        sys.exit(1)
    else:
        print 'CRUNCH report creation successful:\n'
        print stdout_value
        print stderr_value


    s = smtplib.SMTP('localhost')
    msg = MIMEText('Working Directory: %s\nUser e-mail address: %s' %(os.getcwd(), args.user_email))
    msg['From'] = me
    msg['To'] = you
    msg['Subject'] = 'CRUNCH finished successfully'
    s.sendmail(me, [you], msg.as_string())
    s.quit()

    report_page = os.path.join('crunch.unibas.ch/CRUNCH/scratch', os.path.split(os.getcwd())[1])
    s = smtplib.SMTP('localhost')
    msg = MIMEText('Your data was analysed by Crunch. You may find the results at %s/report.\nFor questions, please contact %s\n\nThank you for using Crunch.' %(report_page, me))
    msg['From'] = me
    msg['To'] = args.user_email
    msg['Subject'] = 'CRUNCH finished'
    s.sendmail(me, [args.user_email], msg.as_string())
    s.quit()


if __name__ == '__main__':
    main()
