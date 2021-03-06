#!/usr/bin/env python

import sys, os, re
from string import *
import time
import component_skeleton.main
import subprocess
import datetime
from pylab import *
from scipy import stats
import gzip


def smaller_fa(infile, int_dir, reads_num):
    """This function produces a smaller version of the fasta file from Silvia's output. It takes every 20th line. With the smaller file the adaptor finding runs faster.
    """

    # check first whether input file is gzipped
    gzipped = True
    try:
        fin = gzip.open(infile)
        fin.readline()
    except IOError:
        gzipped = False
    fin.close()

    #get number of lines in complete input file:
    lines_num = reads_num *2 #fasta files contain 2 lines per read
    lines_tot = 0
    if gzipped:
        for l in gzip.open(infile):
            lines_tot += 1
    else:
        for l in open(infile):
            lines_tot += 1


    idle = int(floor(lines_tot/lines_num) + 1)
    print idle

    i = 1
    nr_reads = 0 #total number of reads in smaller file
    tot_reads = 0 #total number of reads in input file


    if gzipped:
        f = gzip.open(infile)
    else:
        f = open(infile)

    outfilename = os.path.join(int_dir, 'smallerFile')
    o = open(outfilename, 'w')

    while True:
        if i == idle:
            line1 = f.readline()
            line2 = f.readline()
            if line1 and line2:
                o.write(line1)
                o.write(line2)
                i = 1
                nr_reads += 1
            else:
                break
        else:
            line1 = f.readline()
            line2 = f.readline()
            if not line1 or not line2:
                break
            i += 1

        tot_reads += 1

    f.close()
    o.close()

    return outfilename, nr_reads, tot_reads



def adaptorSubwordsMatches(in_file, adaptor, out_dir, perlPATH, FMIpath):
    """
    This function computes from a given full adaptor the full matches for adaptor subwords by calling transform.pl by piotr/FMI. 
    """

    adaptorlist = list(adaptor)  #list of individual nucleotides in adaptor
    adaptorlen = len(adaptorlist)
    minadaptorlen = 14

    adaptor_matches = []  #list with tuples of (adaptor subword, full matches)
    matches =[]

    # use adapter prefixes of length 14, 16, 18 and 20. If adapter is shorter than 18 just use 12, 14, 16
    subword_lens = arange(14, min(adaptorlen, 21), 2)
    for i in subword_lens:
        adapt = ''.join(adaptorlist[:i])
        logfile = os.path.join(out_dir, 'adaptorsLog_%s_%i' %(adaptor, i))
        
        command = ' '.join([perlPATH,
                            os.path.join(FMIpath, 'soft', 'filterAdaptors.pl'),
                            '-L',
                            logfile,
                            '-s',
                            '-3',
                            adapt,
                            '-i',
                            in_file,
                            '-F fasta -v > /dev/null 2>&1'
                            ])

        proc = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True
                                ) 
    
        stdout_value, stderr_value = proc.communicate()
        print stdout_value
        print stderr_value

        if proc.poll() > 0:
            print '\tstderr:', repr(stderr_value.rstrip())
            return -1

        log = open(logfile)
        logtext = log.read()
        full_matches = re.search("full matches to 3\'-adaptor :\s*\d+", logtext).group().split()[-1]
        log.close()

        adaptor_matches.append((adapt, int(full_matches)))
        matches.append(int(full_matches))

        #os.system('rm ' + logfile)

    print adaptor
    print adaptor_matches
    print mean(matches)

    plot(subword_lens, matches, label=adaptor)

    return adaptor_matches, mean(matches)



def adaptorDecision(total_count_list, adaptors_list, adaptor_matches_all, outplot):
    """This function looks for the adaptor with highest count of full matches. Then it takes a 20 nucleotide subword of the adaptor and returns it.
    """

    ind = total_count_list.index(max(total_count_list))

    full_adaptor = adaptors_list[ind]
    adaptor_matches_list = adaptor_matches_all[ind] #list of tuples

    ##get some reasonable length of the adaptor
    #derive adaptor_matches_list (the negative of the derivative)
    a = array([i[1] for i in adaptor_matches_list])
    #aprime = [a[i] - a[i+1] for i in arange(len(a)-1)]
    #co = mean(aprime)
    #try:
    #    ind1 = where(aprime >= co)[0][0]
    #except IndexError:
    #    subword = full_adaptor

    try:
        ind1 = where(a < max(a)*0.8)[0][0] -1   #extend adaptor until full matches fall under 80% (this number is not justified) of the maximum matches 
    except IndexError:
        ind1 = len(a) - 1 
        subword = full_adaptor

    subword = ''.join(list(full_adaptor)[:14 + ind1*2]) #14 is minimum length, step of 2
    subword_matches = adaptor_matches_list[ind1][1]

    plot(arange(14,14 + len(a)*2, 2), a)
    plot([14 + ind1*2]*len(a), linspace(max(a), 0, len(a)), label='Chosen adaptor length\n %s' %subword)
    xlabel('Adaptor Length')
    ylabel('Full Matches')
    ylim([0,max(a)])
    xlim([14, 14 + len(a) *2])
    legend(loc='lower left')
    savefig(outplot)

    return subword, subword_matches


def confTotalMatches(N, n, m, outdir):
    """
    N = total number of reads, n = sampled reads, m = matches in sampled reads
    """

    Mrange = arange(m, N-n+m, 100)
    L = [stats.binom.pmf(m,n,float(M)/N) for M in Mrange]
    posts = L/sum(L)

    try:
        Mmin = Mrange[where(cumsum(posts) >= 0.025)][0]
        Mmax = Mrange[where(cumsum(posts) >= 0.975)][0]
    except Exception:
        return 0, 0

    figure()
    plot(arange(m , m +len(posts)*100, 100), posts)
    xlabel('Total Number of Full Matches in Dataset')
    ylabel('Posterior Probability')
    xlim([0, Mmax+Mmin]) #(2*(Mmax+Mmina)/2)
    savefig(os.path.join(outdir, 'PostPlot.pdf'))

    return Mmin, Mmax


def execute(cf):
    """Illumina adaptor removal test
    """

    in_file = cf.get_input("in_file")
    out_dir = cf.get_output("intermediate_dir")
    out_file = cf.get_output("finalAdaptor")
    log_file = cf.get_output("log_file")
    outplot = cf.get_output("plot")
    reads_num =  cf.get_parameter("reads_number", "int")   #factor by how many times the file should be smaller
    perlPATH = cf.get_parameter("perlPATH", "string")
    FMIpath = cf.get_parameter("FMIpath", "string")
    adapters_user = cf.get_parameter("adapters", "string")

    T1 = datetime.datetime.now()

    os.mkdir(out_dir)

    print "Making input fasta file smaller to %i reads" %reads_num

    smaller_filename, nr_reads, tot_reads = smaller_fa(in_file, out_dir, reads_num) 

    T2 = datetime.datetime.now()

    print "Done. Number of reads in smaller file: %s" %nr_reads

    #http://supportres.illumina.com/documents/myillumina/6378de81-c0cc-47d0-9281-724878bb1c30/2012-09-18_illuminacustomersequenceletter.pdf
    adaptors = ['GATCGGAAGAGCTCGTATGCCGTCTTCTGCTTG', #from pdf 
                'ACACTCTTTCCCTACACGACGCTCTTCCGATCT', #from pdf (maybe 5' adapter)
                'GATCGGAAGAGCGGTTCAGCAGGAATGCCGAG', #paired end adapter from pdf
                'TGGAATTCTCGGGTGCCAAGG', #RNA 3' adapter from pdf
                'GATCGGAAGAGCACACGTCTG', #3' end of TrueSeq adaptor from pdf
                'TCGTATGCCGTCTTCTGCTTG'] #from Biter. 5' end of TruSeq adapter from pdf (first adapter in this list)

    # add user specified adapters to the list
    adaptors += adapters_user.split()

    adaptor_matches_all = []  #list of lists of tuples
    mean_matches_all = []    #list of the total summed full adaptor matches for all adaptors

    print "Finding matches for adaptors:\n%s\n" %adaptors

    for adapt in adaptors:
        adaptor_matches, mean_count = adaptorSubwordsMatches(smaller_filename, adapt, out_dir, perlPATH, FMIpath)
        adaptor_matches_all.append(adaptor_matches)
        mean_matches_all.append(mean_count)

    xlabel('prefix length')
    ylabel('full matches')
    legend()
    savefig(outplot)

    res = open(os.path.join(out_dir, 'result'), 'w')
    for a in adaptor_matches_all:
        for sw in a:
            res.write('%s\t%s\n' %(sw[0], sw[1]))
    res.close()


    #get best adaptor with best length
    #final_adaptor, final_adapt_matches = adaptorDecision(total_matches_all, adaptors, adaptor_matches_all, outplot)
    final_adaptor = adaptors[argmax(mean_matches_all)]

    T3 = datetime.datetime.now()

    #get number of full matches in whole file with confidence interval
    #Mmin, Mmax = confTotalMatches(float(tot_reads), float(nr_reads), float(final_adapt_matches), out_dir)

    f = open(out_file, 'w')
    f.write(final_adaptor)
    f.close()

    T4 = datetime.datetime.now()

    lf = open(log_file, 'w')
    log_text = '\n'.join(['Chosen adaptor: %s' %final_adaptor
                          #'The adaptor had %i full matches in a subset of %i reads.' %(final_adapt_matches, nr_reads),
                          #'About %.2f %% of all %i input reads are expected to have a full match.' %((((Mmin+Mmax)/2)/tot_reads)*100, tot_reads)
                          #'With a probability of 95 percent the total number of full matches in the whole dataset of %i reads lies between %i and %i (about %.2f percent)' %(tot_reads, Mmin, Mmax, (((Mmin+Mmax)/2)/tot_reads)*100)
                          #'\nRunning time for adaptor finder:',
                          #'\t-Making file smaller to %i reads: %s' %(nr_reads, T2-T1),
                          #'\t-Finding adaptor: %s' %(T3-T2),
                          #'\t-Overall: %s' %(T4-T1)
                          ])
    lf.write(log_text)
    lf.close()

    #clean up:
    os.system('rm %s' %(smaller_filename))

    return 0


component_skeleton.main.main(execute)
 

    
