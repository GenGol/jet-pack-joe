                title Missile Command
                dosseg
                .model large
                .stack
                .286
                includelib egraph
                extrn timeron:near,timeroff:near,timer:word
                extrn circle:near,plot:near,get:near
                extrn random:near,seedrand:near
                extrn oline:near,aline:near,line:near,xline:near
                extrn inttodec:near,string:near
                extrn load8x8:near,drawchar:near
                extrn clearscreen:near
                public bytesperline,chartable,charheight

                .code


main            proc near

                call init
                call body
                call close

main            endp


init            proc near

                mov ax,@data
                mov ds,ax
                mov es,vidseg

                mov ax,1200h
                mov bl,31h
                int 10h

                mov ax,0012h
                int 10h

                call preppallette

                mov bytesperline,50h

                call load8x8

                mov ax,0000
                int 33h

                mov ax,0
                call seedrand

                call timeron

                ret

init            endp


body            proc near

                call game
                ret

body            endp


game            proc near

                mov score,0
                mov cityhits,0
                mov cityhits+2,0
                mov cityhits+4,0
                mov cityhits+6,0
                mov cityhits+8,0
                mov cityhits+10,0
                mov wavenumber,0
                mov wavepointer,0
                mov nextbonus,100
                mov bonuscitys,0
        gnext:
                call wave
                cmp citys,0
                jle gameover
                inc wavenumber
                mov ax,maxwave
                cmp wavenumber,ax
                jle gsk1
                mov wavenumber,0
                mov wavepointer,0
        gsk1:
                jmp gnext
        gameover:
                ret

game            endp


wave            proc near

                call setup
                call timeloop
                call finish
                ret

wave            endp


close           proc near

                call timeroff

                mov ax,0
                int 33h
                mov ax,3
                int 10h
                mov ax,4c00h
                int 21h

close           endp


setup           proc near

                call wavedata
                call setpallette

                call doscreen

                call tune1

                mov ts+skip,25
                mov ts+time,0
                mov ts+kind,0
                mov ts+address,offset input

                call wavedata
                mov warheadspeed,ax

                mov si,32
                call wavedata
                mov ts[si+skip],ax
                call wavedata
                mov ts[si+value],ax
                mov ts[si+timer],0
                mov ts[si+kind],0
                mov ts[si+address],offset wavehandle

                mov missright,15
                mov missleft,15

                mov termflag,0
                mov lasttask,1
                mov curtask,0
                mov timer,0

                ret

setup           endp


timeloop        proc near

                mov si,curtask
                shl si,5
                mov ax,timer
                sub ax,ts[si+time]
                cmp ax,0
                jl tlnotup
        tlexec:
                mov ax,ts[si+skip]
                add ts[si+time],ax
                mov ax,ts[si+address]
                call ax
        tlnotup:
                cmp termflag,0
                jne tldone
                mov ax,curtask
                cmp ax,lasttask
                jl tlinc
                mov curtask,0
                jmp timeloop
        tlinc:
                inc curtask
                jmp timeloop
        tldone:
                ret

timeloop        endp


finish          proc near

                call mouseoff

                mov bp,0
                mov bx,0
        fnkl1:
                cmp cityhits[bx],0
                jne fnk1
                mov cx,cityx[bx]
                mov dx,citydeck
                mov ax,backcolor
                call drawcity
                mov cx,bp
                mov ax,70
                mul bp
                mov dx,maxy/3
                mov cx,ax
                add cx,100
                mov ax,citycolor
                call drawcity
                call click
                mov ax,points4
                call upscore
                inc bp
                mov ax,timer
                add ax,cdwait
        fnk2:
                cmp ax,timer
                jg fnk2
        fnk1:
                add bx,2
                cmp bx,12
                jl fnkl1

                mov citys,bp

                mov bp,0
        fnkl2:
                cmp missleft,0
                je fnkl3
                dec missleft
                mov ax,missleft
                mov bx,0
                call missileoff
                mov cx,bp
                shl cx,4
                add cx,100
                mov dx,maxy/2
                mov ax,cloudcolor
                mov bx,8
                mov si,offset missile
                call drawchar
                call click
                mov ax,points3
                call upscore
                inc bp
                mov ax,timer
                add ax,mdwait
        fnka1:
                cmp ax,timer
                jg fnka1
                jmp fnkl2
        fnkl3:
                cmp missright,0
                je fnk4
                dec missright
                mov ax,missright
                mov bx,1
                call missileoff
                mov cx,bp
                shl cx,4
                add cx,100
                mov dx,maxy/2
                mov ax,cloudcolor
                mov bx,8
                mov si,offset missile
                call drawchar
                call click
                mov ax,points3
                call upscore
                inc bp
                mov ax,timer
                add ax,mdwait
        fnka2:
                cmp ax,timer
                jg fnka2
                jmp fnkl3
        fnk4:

                call bonuscity

                ret

finish          endp


doscreen        proc near

                mov ax,0
                mov cx,480
                mov di,0
                call clearscreen

                mov ax,groundcolor
                mov bx,30
        dslp1:
                mov dx,maxy-20
                add dx,bx
                mov di,dx
                mov cx,0
                mov si,maxx
                cmp bx,20
                jg dssk1
                call line
        dssk1:
                sub dx,30
                mov di,dx
                mov cx,xlaunch1
                mov si,cx
                sub cx,bx
                add si,bx
                call line
                mov cx,xlaunch2
                mov si,cx
                sub cx,bx
                add si,bx
                call line
                dec bx
                jg dslp1

                mov dx,citydeck
                mov bx,0
        dslp2:
                cmp cityhits[bx],0
                jg dsncd
                mov cx,cityx[bx]
                mov ax,citycolor
                call drawcity
        dsncd:
                add bx,2
                cmp bx,10
                jle dslp2

                call fillbase

                mov ax,0
                call upscore

                call mouseon

                ret

doscreen        endp


input           proc near

                call mothand
                call getbuttons
                push bx
                and butflag,bx
                xor butflag,bx
        msdrop:
                test butflag,1
                jz mssk1
                cmp missleft,0
                je mssk1
                dec missleft
                mov bx,0
                mov ax,missleft
                call missileoff
                mov cx,xlaunch1
                call startupmiss
                call crosson
                mov bx,0
                call startsound
        mssk1:
                test butflag,2
                jz mssk2
                cmp missright,0
                je mssk2
                dec missright
                mov bx,1
                mov ax,missright
                call missileoff
                mov cx,xlaunch2
                call startupmiss
                call crosson
                mov bx,0
                call startsound
        mssk2:
                pop butflag
                mov ah,1
                int 16h
                jz msdone
                mov ah,0
                int 16h
                mov termflag,1
                 cmp al,0dh
                 jne msdone
                 call close
                 mov ax,4c00h
                 int 21h
        msdone:
                ret

input           endp


wavehandle      proc near

                mov cx,ts[si+value]
                cmp cx,-1
                je wvsk2
                push si
        wvlp1:
                push cx
                mov bx,-1
                mov cx,-1
                mov dx,0
                call startwarhead
                pop cx
                loop wvlp1
                pop si
                call wavedata
                mov ts[si+skip],ax
                call wavedata
                mov ts[si+value],ax
                ret
        wvsk2:
                cmp lasttask,1
                jg wvsk1
                mov termflag,1
        wvsk1:
                ret

wavehandle      endp


wavedata        proc near

                push bx
                mov bx,wavepointer
                mov ax,wave0[bx]
                add wavepointer,2
                pop bx
                ret

wavedata        endp


upscore         proc near

                pusha

                mov si,ax
                mov bx,offset scorestring
                mov ax,score
                call inttodec
                mov ax,groundcolor
                mov cx,10
                mov dx,maxy-10
                call string
                add score,si
                mov ax,score
                call inttodec
                mov ax,15
                call string

                popa
                ret

upscore         endp


drawcity        proc near

                ;cx,dx=x,y position

                pusha

                add cx,city1x
                add dx,city1y
                mov bx,city1h
                mov si,offset city1
                call drawchar
                sub cx,city1x
                sub dx,city1y

                add cx,city2x
                add dx,city2y
                mov bx,city2h
                mov si,offset city2
                call drawchar
                sub cx,city2x
                sub dx,city2y

                add cx,city3x
                add dx,city3y
                mov bx,city3h
                mov si,offset city3
                call drawchar
                sub cx,city3x
                sub dx,city3y

                add cx,city4x
                add dx,city4y
                mov bx,city4h
                mov si,offset city4
                call drawchar
                sub cx,city4x
                sub dx,city4y

                add cx,city5x
                add dx,city5y
                mov bx,city5h
                mov si,offset city5
                call drawchar
                sub cx,city5x
                sub dx,city5y

                add cx,city6x
                add dx,city6y
                mov bx,city6h
                mov si,offset city6
                call drawchar
                sub cx,city6x
                sub dx,city6y

                add cx,city7x
                add dx,city7y
                mov bx,city7h
                mov si,offset city7
                call drawchar
                sub cx,city7x
                sub dx,city7y

                add cx,city8x
                add dx,city8y
                mov bx,city8h
                mov si,offset city8
                call drawchar

                popa
                ret

drawcity        endp


missileon       proc near

                pusha
                shl ax,1
                mov bp,ax
                shl bx,1
                mov cx,xlaunch1[bx]
                mov dx,ylaunch
                mov bx,8
                mov si,offset missile
                mov ax,cloudcolor

                add cx,ds:missilex[bp]
                sub cx,3
                add dx,ds:missiley[bp]
                call drawchar
                popa
                ret

missileon       endp


missileoff      proc near

                pusha
                shl ax,1
                mov bp,ax
                shl bx,1
                mov cx,xlaunch1[bx]
                mov dx,ylaunch
                mov bx,8
                mov si,offset missile
                mov ax,groundcolor

                add cx,ds:missilex[bp]
                sub cx,3
                add dx,ds:missiley[bp]
                call drawchar
                popa
                ret

missileoff      endp


fillbase        proc near

                mov ax,0
        fbloop1:
                mov bx,0
                call missileon
                mov bx,1
                call missileon
                inc ax
                cmp ax,15
                jl fbloop1
                ret

fillbase        endp


click           proc near

                push bx
                push ax
                in al,61h
                and al,0feh
                or al,2
                out 61h,al
                mov bx,timer
                add bx,2
        clsk1:
                cmp bx,timer
                ja clsk1
                and al,0fdh
                out 61h,al
                pop ax
                pop bx
                ret

click           endp


tune1           proc near

                mov ax,3
        t1lp2:
                mov bx,3000
                mov cx,45
                mov dx,10
        t1lp1:
                call tone
                add bx,130
                dec dx
                jg t1lp1
                dec ax
                jg t1lp2
                ret

tune1           endp


tune2           proc near

                mov cx,180
                mov bx,2000
                call tone
                mov bx,1500
                call tone
                mov bx,2000
                call tone
                mov bx,1500
                call tone
                mov bx,2000
                call tone
                mov bx,1500
                call tone
                mov ax,timer
                add ax,500
        t2pt1:
                cmp ax,timer
                jg t2pt1
                ret

tune2           endp


tone            proc near

                push ax
                push bx
                in al,61h
                or al,3
                out 61h,al
                mov al,0b6h
                out 43h,al
                mov al,bl
                out 42h,al
                mov al,bh
                out 42h,al
                mov ax,timer
                add ax,cx
        tnl1:
                mov bx,ax
                sub bx,timer
                cmp bx,0
                jg tnl1
                in al,61h
                and al,0fch
                out 61h,al
                pop bx
                pop ax
                ret

tone            endp


bonuscity       proc near

                mov ax,score
                cmp ax,nextbonus
                jl bcdone
                inc bonuscitys
                mov ax,bonusgap
                add nextbonus,ax
                cmp bonuscitys,0
                je bcdone
                cmp citys,6
                je bcdone
                mov bx,0
                call random
                and ax,0fh
                mov cx,ax
                inc cx
                mov bx,0
        bclp1:
                sub bx,2
                jge bcsk2
                mov bx,10
        bcsk2:
                cmp cityhits[bx],0
                je bclp1
                loop bclp1
                mov cityhits[bx],0
                inc citys
                call tune2
                cmp citys,6
                jl bonuscity
        bcdone:
                ret

bonuscity       endp


preppallette    proc near

                mov ax,1002h
                push es
                mov bx,ds
                mov es,bx
                mov dx,offset preppall
                int 10h
                pop es
                ret

preppallette    endp


setpallette     proc near

                pusha
                push es
                mov bx,ds
                mov es,bx

                mov bx,27
                mul bx
                mov si,ax
                mov cx,24
                add si,offset palltable
                mov di,offset utilpall

                rep movsb

                mov ax,[si]
                mov bl,[si+2]
                mov cx,8
        spllp2:
                mov [di],ax
                mov [di+2],bl
                add di,3
                loop spllp2

                mov ax,1012h
                mov bx,0
                mov cx,16
                mov dx,offset utilpall
                int 10h

                pop es
                popa
                ret

setpallette     endp



                include starts.asm


                include maint.asm


                include mouse.asm


                .data


vidseg          dw 0a000h
dataseg         dw @data
bytesperline    dw 0
maxtask         dw 55
maxwave         dw 19

maxx            equ 639
maxy            equ 479
cursminx        dw 5
cursminy        dw 5
cursmaxx        dw 634
cursmaxy        dw 419
xlaunch1        dw 205
xlaunch2        dw 434
ylaunch         dw 429
citydeck        dw 462
splitdeck       dw 160
clouddeck       dw 429
nukex           dw 35,17,46
nukey           dw -25,-19,-19
nuket           dw 0,250,600
cityx           dw 12,106,241,335,470,564
targetx         dw 44,138,205,273,367,434,502,596
missilex        dw 0,-7,7,-14,0,14,-21,-7,7,21,-28,-14,0,14,28
missiley        dw 3,10,10,17,17,17,24,24,24,24,33,33,33,33,33

backcolor       dw 0
cloudcolor      dw 4
mcolor1         dw 3
mcolor2         dw 1
groundcolor     dw 6
citycolor       dw 7
warheadcolor1   dw 3
warheadcolor2   dw 2
warcloudcolor   dw 5

cloudrad        dw 45
cloudspeed      dw 80
miss1speed      dw 2
wartracespeed   dw 3
tracewait       dw 300
bonusgap        dw 250
cdwait          dw 400
mdwait          dw 150

points1         dw 2
points2         dw 4
points3         dw 1
points4         dw 10

frequ0          dw 1,2,20
frequ1          dw 50,20,20
frequc          dw 10,6 ,60

wave0           dw 5,30,2000,4,10000,4,10000,4,0,-1
wave1           dw 5,30,2000,4,10000,5,10000,6,0,-1
wave2           dw 5,20,2000,5,10000,6,10000,2,19000,2,9000,8,0,-1
wave3           dw 2,20,2000,6,10000,3,10000,1,1500,1,1500,1,1500,1,1500,8,0,-1
wave4           dw 2,18,2000,3,10000,3,10000,3,10000,3,10000,5,10000,5,0,-1
wave5           dw 2,17,2000,4,10000,4,10000,8,10000,2,10000,2,10000,5,0,-1
wave6           dw 3,16,2000,3,10000,3,10000,3,10000,3,10000,5,10000,5,0,-1
wave7           dw 3,15,2000,4,10000,4,10000,8,10000,2,10000,2,10000,5,0,-1
wave8           dw 3,14,2000,4,5000,4,5000,4,5000,4,5000,4,5000,4,0,-1
wave9           dw 7,13,4000,5,4000,5,4000,5,3000,3,3000,3,3000,3,5000,5,0,-1
wave10          dw 7,12,3000,4,4000,4,3500,4,3000,4,2500,4,2000,4,1500,4,0,-1
wave11          dw 7,12,3000,6,6000,6,6000,6,6000,6,10000,4,7000,4,0,-1
wave12          dw 1,9,7000,2,5000,2,5000,2,5000,2,5000,2,0,-1
wave13          dw 1,9,7000,2,8000,2,8000,3,5000,3,5000,2,8000,6,0,-1
wave14          dw 1,12,2000,6,7000,6,7000,6,7000,3,4000,3,4000,7,4000,2,0,-1
wave15          dw 2,11,2000,4,5000,4,5000,4,5000,4,5000,4,5000,4,5000,4,0,-1
wave16          dw 3,10,2000,3,5000,3,5000,3,5000,3,5000,3,5000,3,5000,3,0,-1
wave17          dw 4,12,2000,8,8000,8,8000,8,8000,1,5000,1,5000,6,0,-1
wave18          dw 5,11,2000,5,3000,5,3000,5,3000,5,3000,5,3000,5,0,-1
wave19          dw 7,12,2000,4,10000,4,10000,8,10000,2,10000,2,10000,5,0,-1







preppall        db 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,0

palltable       db 0,16,32, 63,63,0, 63,0,0, 63,63,63, 48,48,48, 40,40,40
                db 32,24,0, 32,32,32, 0,0,0
                db 32,10,10, 0,0,59, 10,63,10, 63,63,63, 63,63,0, 0,48,48
                db 32,32,10, 0,0,48, 63,63,63
                db 0,0,0, 0,32,0, 0,0,32, 63,63,63, 0,63,0, 0,0,63
                db 15,32,32, 48,24,0, 63,0,63
                db 63,63,63, 48,48,48, 32,32,32, 0,0,0, 0,0,0, 20,20,20
                db 25,25,25, 0,32,32, 0,0,0



                include shapes.asm

charheight      dw 8
chartable       db 2048 dup ( 0 )

utilpall        db 48 dup( 0 )


mousex          dw 200
mousey          dw 200
termflag        dw 0
curtask         dw 0
lasttask        dw 0
butflag         dw 0
missleft        dw 0
missright       dw 0
nextbonus       dw 0
bonuscitys      dw 0
warheadspeed    dw 20
score           dw 0
scorestring     db 0,0,0,0,0,0,0,0
cityhits        dw 0,0,0,0,0,0
citys           dw 0
wavenumber      dw 0
wavepointer     dw 0

ts              dw 64 dup(16 dup(0))    ;space for up to 64 tasks with 32 bytes

time            equ 0                   ;position names for all tasks
skip            equ 2
kind            equ 4
address         equ 6
xpos            equ 8
ypos            equ 10

deltax          equ 12                  ;additional position names for
deltay          equ 14                  ; missiles types 1,2,3,5
decision        equ 16
color1          equ 18
color2          equ 20
direction       equ 22
lastx           equ 24
lasty           equ 26
lastdec         equ 28
target          equ 30

radius          equ 12                  ;additional position names for
maxradius       equ 28                  ;cloud 4
color           equ 18

mode            equ 12                  ;position names for wave
clicks          equ 14

altskip         equ 12
value           equ 14
cycles          equ 16
notepointer     equ 18
nextnote        equ 20


                end main

