#! /usr/bin/env python
#coding=utf-8
##############################################
# Copyright (c) 2021-2023
# ADVA Optical Networking
# This is the DPDK readiness checklist
#  
##############################################
from __future__ import print_function
import os
import platform
import shutil


def read_sys_info(fn):
    try:
        with open(fn, "r") as f:
            s = f.read().rstrip()
    except:
        s = ""
    return s


def print_ddr_speed():
    ddr_speed = 'DDR speed'
    s = os.popen('dmidecode -t 17').read().split('\t')
    for z in s:
        if 'Speed' in z:
            freq = z.split(':')[1].split()
# ['1067', 'MT/s']
# ['Unknown']
            if len(freq) > 1:
                break

    if (not freq):
        print ("[error] Can't read %s" % (ddr_speed))
        return

    # DDR channel is encoded in letter:
    # Locator: DIMM_A1   <-- A and B are different memory channels
    # Locator: DIMM_B1
    s = os.popen('dmidecode -t memory | grep Locator').read().split('\t')
    n = 0
    dimm = 'unknown'
    for z in s:
        if 'DIMM' in z:
            tmp = z.split(':')[1]
            if tmp[len(tmp)-3] != dimm[len(dimm)-3]:
                n = n + 1
                dimm = tmp

    print ("[info] %s %s %s, %d channels" % (ddr_speed, freq[0], freq[1], n))


def check_cpu_freq():
    cur_freq = ''
    max_freq = ''
    cpu_type = '?'

    s = os.popen('dmidecode -t 4').read().split('\t')
    for z in s:
        if ('Family' in z) and ('Unknown' in z): # Empty CPU socket?
            break

        if 'Version' in z:
            cpu_type = z.split(':')[1].rstrip('\n')
        elif 'Max Speed' in z:
            max_freq = z.split(':')[1].split()[0]
        elif 'Current Speed:' in z:
            cur_freq = z.split(':')[1].split()[0]

    if (not cur_freq) or (not max_freq):
        print ("[error] Can't read CPU frequency ")
        return

    print ("[info] CPU%s" % (cpu_type))

    cur_freq = int(cur_freq)
    max_freq = int(max_freq)

    if cur_freq < max_freq:
        print ("[warning] CPU frequency %d is less than max %d" % (cur_freq, max_freq))
    else:
        print ("[OK] CPU frequency is max (%d MHz)" % (max_freq))


def check_cpu_scaling_governor():
    x = read_sys_info('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor')
    if not x:
        try:
            x = os.popen('tuned-adm active').read().split(':')[1].rstrip('\n') 
        except:
            pass

    if not x:
        x = '?'

    if 'performance' in x or 'realtime' in x:
        print ("[OK] CPU scaling is", x)
    else:
        print ("[error] CPU scaling is", x)
        print ("\tconsider to do: tuned-adm profile latency-performance")


def check_swap_enabled():
    fn = '/etc/fstab'

    with open(fn,'r') as f:
        for line in f:
            if not line.startswith('#'):
                if 'swap' in line:
                    print ("[error] swap is enabled in %s" % fn)
                    return True
        
    print ("[OK] swap is disabled")
    return False

def check_huge_pages():
    s = read_sys_info('/proc/meminfo').split('\n')
    n = 0
    sz = 0
    for x in s:
        if 'HugePages_Total' in x:
            a = x.split()
            n = int(a[1])
        if 'Hugepagesize' in x:
            a = x.split()
            sz = int(a[1])
               
    if n>0:
        print ("[OK] HugePages_Total: %d, %d kB each" % (n, sz))
    else:
        print ("[error] HugePages_Total: %d" % n)

def check_transparent_huge_pages():
    # Based on the 3.10 kernel operating system, the transparent huge page function 
    # (THP) is turned on by default. THP will cause the operating system 
    # to see that there are large pages and allocate large pages.
    # When large pages cannot be allocated, traditional 4KB pages are allocated.
    # The setting returned in brackets is your current setting
    # To disable THP:
    # echo never > /sys/kernel/mm/transparent_hugepage/enabled
    err_msg = 'OK'
    x = 'not found'
    s = read_sys_info('/sys/kernel/mm/transparent_hugepage/enabled').split()

    if s:
        err_msg = 'error'
        for x in s:
            if '[' in x:
                if x == '[never]':
                    err_msg = 'OK'
                break
                
    print ("[%s] transparent_hugepage/enabled: %s" % (err_msg, x))

    if err_msg != 'OK':
        print ("\t - please add transparent_hugepage=never to cmdline")

def check_service(service):
    stat = os.system('systemctl status '+service+' >/dev/null 2>&1')
    if stat != 0:
        print ('[OK] '+service+' not active')
    else:
        print ("[error] - please deactivate %s:\
        \n\tsystemctl stop %s \n\tsystemctl disable %s" % (service,service,service))

#
# isolcpus
# • Remove cores from the general kernel SMP balancing and scheduler algorithms
# rcu_nocbs
# • prevents Read-Copy-Update (RCU) callback routines from being executed on the targeted cores
# nohz_full
# • Disables kernel timer tick interrupt. Triggered at a periodic interval to keep track of kernel statistics such as CPU and
# memory usage
# https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux_for_real_time/7/html/tuning_guide/offloading_rcu_callbacks
# 
# domain removes the CPUs from the scheduling algorithm
# https://ubuntu.com/blog/real-time-kernel-tuning
def check_isol_cpu_cores():
    parms = ('isolcpus','nohz_full','rcu_nocbs')
    vals=["0","0","0"]
    
    s = read_sys_info('/proc/cmdline').split()
    for x in s:
        for index, y in enumerate(parms):
            if y in x:
                a = x.split('=')
                print ("[OK] %s" % a)
                # isolcpus=managed_irq,domain,1-12
                b = a[1].split(',')
                vals[index]=b[-1]

    # print vals
    missed_parms = False
    for index, item in enumerate(vals):
        if item == "0":
            print ("[error] - please specify %s " % parms[index])
            missed_parms = True

    if missed_parms:
        return

    result = all(element == vals[0] for element in vals)
    if not result:
        print ("[error] %s not %s not %s" % (vals[0], vals[1], vals[2]))


# Depending on your system, you'll find it in any one of these:
# /proc/config.gz
# /boot/config
# /boot/config-$(uname -r)
def check_linux_config(cfg):
    paths = ('/proc/config.gz','/boot/config-'+os.uname()[2]) #,'/boot/config'

    for fn in paths:
        if os.path.exists(fn) :
            if '.gz' in fn:
                s = os.popen('cat '+ fn +' | gunzip 2>/dev/null').read()
            else:
                s = os.popen('cat '+ fn).read()

            if cfg in s:
                print ("[OK]", cfg)
                return

    print ("[error] - {} not found in {}".format(cfg, fn))

def check_hyperthreading():
    s = os.popen('lscpu').read().split('\n')
    n = 1
    for x in s:
        if 'Thread(s) per core' in x:
            n = int(x.split(':')[1])
            break

    if n>1:
        print ("[warning] - HT enabled")
    else:
        print ("[OK] HT disabled")

def is_centos():
    return platform.dist()[0] == 'centos'


def is_selinux_enabled():
    if shutil.which('sestatus'):
        s = os.popen('sestatus').read()
        return 'disabled' in s
    else:
        return True

def check_cmdline(cfg):
    s = read_sys_info('/proc/cmdline').split()
    for x in s:
        if cfg in x:
            print ("[OK]", cfg)
            return
    
    print ("[error] - please add %s to cmdline" % cfg)



if __name__ == "__main__":

    print
    msg = "# Checking DPDK system readyness, kernel: "+os.uname()[2]
    print (msg)
    #print('\t', platform.dist())
    print ("="*len(msg))
    check_cpu_freq()
    print_ddr_speed()
    check_hyperthreading()
    check_swap_enabled()
    check_huge_pages()
    check_isol_cpu_cores()
    check_cmdline('intel_iommu=on')
    check_cmdline('iommu=pt')

    # Completely eliminate timer interrupts on a set of cores
    check_linux_config('CONFIG_NO_HZ_FULL=y')
    check_cmdline('nohz=on')

    # Disables clocksource stability check interrupt for the Time Stamp Counter on all cores
    check_cmdline('tsc=reliable')

 #   if is_centos():
    if is_selinux_enabled():
        print ("[OK] selinux disabled")
    else:
        check_cmdline('selinux=0')
        check_cmdline('enforcing=0')

    check_cmdline('intel_pstate=disable')
    check_cmdline('nmi_watchdog=0')
    check_cmdline('audit=0')
    check_cmdline('mce=off')
    check_cmdline('kthread_cpus=0')
    check_cmdline('irqaffinity=0')
    check_cmdline('skew_tick=1')
    check_cmdline('nosoftlockup')
    check_cpu_scaling_governor()
    check_transparent_huge_pages()
    check_service('irqbalance')
    check_service('impi')
    check_service('ipmievd')

