import subprocess, os, datetime, time

def create_motevo_param_file(prior, param_filename, site_filename, prior_filename, genome, priordiff=0.05, minposterior=0.0):
    param_file = open(param_filename, 'w')
    param_file.write('\n'.join([
        'refspecies %s' % genome,
        'TREE (%s: 1)' % genome,
        'Mode TFBS',
        'EMprior 0',
        'priordiff %f' % priordiff,
        'markovorderBG 0',
        'bgprior %f' % prior, 
        'bg A 0.25',
        'bg T 0.25',
        'bg G 0.25',
        'bg C 0.25',
        'restrictparses 0',
        'sitefile %s' % site_filename,
        'priorfile %s' % prior_filename,
        'minposterior %f' % minposterior,
        'printsiteals 0',
        ]))
    param_file.close()
    return 0


def run_motevo(motevo_path, WM, prior, sequences, interm_dir, genome):
    stime = datetime.datetime.now()
    motifName = os.path.basename(WM)
    print '\nrunnig Motevo for %s' % motifName
    siteFilename = os.path.join(interm_dir, '%s.sites' % motifName)
    priorFilename = os.path.join(interm_dir, '%s.priors' % motifName)
    paramFilename = os.path.join(interm_dir, '%s.params' % motifName)
    create_motevo_param_file(prior, paramFilename, siteFilename, priorFilename, genome)
    cmd = ' '.join([
        motevo_path,
        sequences,
        paramFilename,
        WM ])
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr= subprocess.PIPE,
                            shell=True)    
    while proc.poll() == None:
        # print proc.poll()
        time.sleep(10)
        now = datetime.datetime.now()
        if (now - stime).seconds > 600:
            os.kill(proc.pid, signal.SIGKILL)
            os.waitpid(-1, os.WNOHANG)
            print '\nMotevo weight matrix refinement did not converge.\n'
            return None
    print proc.stderr.read()
    print proc.stdout.read()
    if proc.poll() > 0:
        print '\nMotevo weight matrix refinement not successful.\n'
        return None
    else:
        print '\nMotevo weight matrix refinement converged.\n'
        return siteFilename
    return siteFilename
