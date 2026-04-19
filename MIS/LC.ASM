                title Light Cycles
                dosseg
                .model large
                .286
                .stack
                includelib egraph
                extrn plot:near,get:near,line:near,circle:near
                extrn timeron:near,timeroff:near,timer:word
                public bytesperline
                .code

main            proc far

                call init
                call body
                call close
                mov ax,4c00h
                int 21h

main            endp


init            proc near

                mov ax,@data            ;load seg regs
                mov ds,ax
                mov es,vidseg

                mov ax,1200h            ;turn on default palette loading
                mov bl,31h
                int 10h

                mov ax,0012h            ;set video mode 13h
                int 10h

                mov bytesperline,80

                call timeron

                ret

init            endp


body            proc near


                call setup
                call mainloop
                call explode

                mov ax,0005h            ;set write mode to 0
                mov dx,3ceh
                out dx,ax

                mov ax,0ff08h           ;set bitmask
                out dx,ax

                mov ax,1301h            ;print message
                mov bx,messcolor
                mov cx,20
                mov dx,0101h
                mov bp,offset message1
                mov es,dataseg
                int 10h
                mov es,vidseg
        confirm:
                mov ah,0                ;get key
                int 16h
                cmp al,"y"              ;if key is "y" then run again
                je body
                cmp al,"n"
                jne confirm
                ret

body            endp


close           proc near

                call timeroff

                mov ax,0003h            ;set text mode
                int 10h
                ret

close           endp


setup           proc near

                mov ax,backcolor        ;clear screen to black
                mov cx,32000
                mov di,0
                rep stosw

                mov ax,bordcolor
                mov cx,0                ;draw border
                mov dx,0
                mov si,maxx
                mov di,0
                call line
                mov di,maxy
                mov cx,maxx
                call line
                mov cx,0
                mov dx,maxy
                call line
                mov di,0
                mov si,0
                call line

                mov ax,x1start          ;set starting coordinates
                mov x1,ax
                mov ax,y1start
                mov y1,ax
                mov ax,x2start
                mov x2,ax
                mov ax,y2start
                mov y2,ax

                mov ax,d1start          ;set starting directions
                mov d1,ax
                mov ax,d2start
                mov d2,ax

                mov dead1,0             ;set dead flags
                mov dead2,0

                mov cx,x1               ;draw first cycles
                mov dx,y1
                mov ax,color1
                call plot
                mov cx,x2
                mov dx,y2
                mov ax,color2
                call plot

                mov ax,nextinit1
                mov nexttime1,ax
                mov ax,nextinit2
                mov nexttime2,ax
                mov timer,0

                ret

setup           endp


mainloop        proc near

                mov ah,1
                int 16h
                jz nokey

                mov ah,0
                int 16h
                cmp al,0
                jne mlpl1
        mlpl2:
                cmp ah,77
                jne skb
                inc d2
                and d2,3
            skb:
                cmp ah,75
                jne skd
                dec d2
                and d2,3
            skd:
                jmp skf
        mlpl1:
                cmp al,"z"
                jne ske
                dec d1
                and d1,3
            ske:
                cmp al,"x"
                jne skf
                inc d1
                and d1,3
            skf:
nokey:
       player1:
                mov ax,nexttime1
                sub ax,timer
                cmp ax,0
                jg player2
                mov ax,wait1
                add nexttime1,ax

                mov cx,x1
                mov dx,y1
                mov ax,trail1
                call plot

                cmp d1,0
                jne skm
                dec y1
            skm:
                cmp d1,1
                jne skn
                inc x1
            skn:
                cmp d1,2
                jne sko
                inc y1
            sko:
                cmp d1,3
                jne skp
                dec x1
            skp:
                mov cx,x1
                mov dx,y1
                call get
                cmp ax,backcolor
                je sku
                mov dead1,1
            sku:
                mov ax,color1
                call plot
        player2:
                mov ax,nexttime2
                sub ax,timer
                cmp ax,0
                jg maindone
                mov ax,wait2
                add nexttime2,ax

                mov cx,x2
                mov dx,y2
                mov ax,trail2
                call plot
 
                cmp d2,0
                jne skq
                dec y2
            skq:
                cmp d2,1
                jne skr
                inc x2
            skr:
                cmp d2,2
                jne sks
                inc y2
            sks:
                cmp d2,3
                jne skt
                dec x2
            skt:
                mov cx,x2
                mov dx,y2
                call get
                cmp ax,backcolor
                je skv
                mov dead2,1
            skv:
                mov ax,color2
                call plot
        maindone:
                mov ax,dead1
                add ax,dead2
                jne mlexit
                jmp mainloop
mlexit:
                ret

mainloop        endp


explode         proc near

                mov bx,0
        exloopa:
                cmp dead1,0
                je exska
                mov cx,x1
                mov dx,y1
                mov ax,color1
                call circle
        exska:
                cmp dead2,0
                je exskb
                mov cx,x2
                mov dx,y2
                mov ax,color2
                call circle
        exskb:
                call delay
                inc bx
                cmp bx,maxrad
                jle exloopa

                mov bx,0
	exloopb:
                cmp dead1,0
		je exskc
                mov cx,x1
                mov dx,y1
		mov ax,trail1
                call circle
	exskc:
                cmp dead2,0
		je exskd
                mov cx,x2
                mov dx,y2
		mov ax,trail2
                call circle
	exskd:
                call delay
                inc bx
                cmp bx,maxrad
                jle exloopb

                mov bx,0
	exloopc:
                cmp dead1,0
		je exske
                mov cx,x1
                mov dx,y1
		mov ax,0
                call circle
	exske:
                cmp dead2,0
		je exskf
                mov cx,x2
                mov dx,y2
		mov ax,0
                call circle
	exskf:
                call delay
                inc bx
                cmp bx,maxrad
                jle exloopc

                ret

explode         endp


delay           proc near

                push ax

                mov ax,timer
                add ax,time
        dl1:
                cmp ax,timer
                jg dl1

                pop ax
                ret

delay           endp



                .data


bytesperline    dw 0
vidseg          dw 0a000h
dataseg         dw @data
message1        db "Play again? (y or n)"
messcolor       dw 1
backcolor       dw 0
bordcolor       dw 1
maxx            equ 639
maxy            equ 479
color1          dw 10
color2          dw 12
trail1          dw 2
trail2          dw 4
x1start         dw maxx/2-maxx/40
y1start         dw maxy-maxy/10
x2start         dw maxx/2+maxx/40
y2start         dw maxy-maxy/10
d1start         dw 0
d2start         dw 0
time            dw 30
maxrad          dw 20
x1              dw 0
y1              dw 0
x2              dw 0
y2              dw 0
d1              dw 0
d2              dw 0
dead1           dw 0
dead2           dw 0
wait1           dw 9
wait2           dw 9
nexttime1       dw 0
nexttime2       dw 0
nextinit1       dw 1000
nextinit2       dw 1000


                end

