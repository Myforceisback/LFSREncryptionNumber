https://disk.yandex.ru/d/qv_uxhMuTPMgpA
import numpy as np
import math
from pylfsr import LFSR

def LFRS_RANDOM_NUMBER(Fstate, startZero):
    L = LFSR()
    s = startZero
    state = Fstate #[1,0,1,0]
    fpoly = [3,2]
    L = LFSR(initstate = state, fpoly = fpoly, counter_start_zero = s)
    print('count \t\t state \t\t outbit')
    print('-'*50)
    for _ in range(15):
        print(L.count,"\t",L.state,'',L.outbit,sep='\t')
        L.next()
    print('-'*52)
    print('Output: ',L.seq)
    return L.seq

def numsys(num):
    q = [0] * 4
    finarr = [0]
    list = ['0:0000',
            '1:0001',
            '2:0010',
            '3:0011',
            '4:0100',
            '5:0101',
            '6:0110',
            '7:0111',
            '8:1000',
            '9:1001',
            ]
    a = str(num)
    width = len(a)
    for i in range(width):
        x = list[int(a[i])]
        y = x.rsplit(':')
        z = str(y[1])
        for j in range(4):
            q[j] = int(z[j])
        if (q[0] == 0):
            st = True
            fin = LFRS_RANDOM_NUMBER(q, startZero=st)
            for g in range(15):
                finarr.append(int(fin[g]))
        else:
            st = False
            fin = LFRS_RANDOM_NUMBER(q, startZero=st)
            for g in range(15):
                finarr.append(int(fin[g]))
    return finarr

def main():
    print("Number encryption based on LFSR generator")
    number = input("Enter the number for encryption -> ")
    gg = numsys(number)
    schet = len(gg)
    whrite_txt = open('res.txt', 'w')
    for i in range(schet):
        whrite_txt.write(str(gg[i]))
    whrite_txt.close()
main()