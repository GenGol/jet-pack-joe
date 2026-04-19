endtask         proc near

                mov di,curtask
                shl di,5
                mov si,lasttask
                shl si,5
                mov cx,16
                add si,offset ts
                add di,offset ts
                mov es,dataseg
                rep movsw
                mov es,vidseg
                dec lasttask
                ret

endtask         endp


startupmiss     proc near

                mov ax,lasttask
                cmp ax,maxtask
                jl sumcd
                ret
        sumcd:
                mov bx,cx
                push cx
                inc lasttask
                mov si,lasttask
                shl si,5
                mov ts[si+kind],1
                mov ax,miss1speed
                mov ts[si+skip],ax
                mov ax,timer
                mov ts[si+time],ax
                mov ts[si+address],offset upmissile
                mov cx,mousex
                mov dx,mousey
                push si
                call starttracer
                pop si
                mov ts[si+lasty],dx
                mov ts[si+lastx],cx

                pop ax
                mov ts[si+xpos],ax
                sub ax,cx
                mov ts[si+deltax],ax

                mov ax,ylaunch
                mov ts[si+ypos],ax
                sub ax,dx
                mov ts[si+deltay],ax

                mov ts[si+direction],-1

                mov ax,ts[si+deltay]
                sub ax,ts[si+deltax]
                sar ax,1
                mov ts[si+decision],ax

                mov ax,mcolor1
                mov ts[si+color1],ax
                mov ax,mcolor2
                mov ts[si+color2],ax
                cmp ts[si+deltax],0
                jl smurev
                jmp smudone
        smurev:
                neg ts[si+deltax]
                neg ts[si+direction]
        smudone:
                ret

startupmiss     endp


startcloud      proc near

                mov bx,lasttask
                cmp bx,maxtask
                jl sccd
                ret
        sccd:
                mov si,lasttask
                inc si
                shl si,5
                mov bx,cloudspeed
                mov ts[si+skip],bx
                mov bx,timer
                mov ts[si+time],bx
                mov ts[si+kind],4
                mov ts[si+address],offset cloud
                mov ts[si+xpos],cx
                mov ts[si+ypos],dx
                mov ts[si+radius],0
                mov ts[si+direction],1
                mov bx,clouddeck
                sub bx,dx
                cmp bx,cloudrad
                jle scsk1
                mov bx,cloudrad
        scsk1:
                cmp bx,2
                jg scsk2
                mov bx,3
        scsk2:
                mov ts[si+maxradius],bx
                mov ts[si+color],ax
                inc lasttask
                ret

startcloud      endp


nukecity        proc near

                push cloudrad
                push clouddeck
                mov cloudrad,23
                mov clouddeck,1000
                shl bx,1
                mov ax,cityx[bx]
                mov bx,0
        ncloop:
                push si
                push ax
                push bx
                mov dx,citydeck
                add dx,nukey[bx]
                mov cx,nukex[bx]
                add cx,ax
                mov ax,nuket[bx]
                add timer,ax
                mov ax,warcloudcolor
                call startcloud
                pop bx
                mov ax,nuket[bx]
                sub timer,ax
                pop ax
                pop si
                add bx,2
                cmp bx,6
                jl ncloop

                pop clouddeck
                pop cloudrad
                push si
                mov bx,2
                call startsound
                pop si
                ret

nukecity        endp


starttracer     proc near

                push bx
                inc lasttask
                mov si,lasttask
                shl si,5
                mov ts[si+kind],1
                mov ax,miss1speed
                mov ts[si+skip],ax
                mov ax,timer
                add ax,tracewait
                mov ts[si+time],ax
                mov ts[si+address],offset tracer
                mov ts[si+lasty],dx
                mov ts[si+lastx],cx

                pop ax
                mov ts[si+xpos],ax
                sub ax,cx
                mov ts[si+deltax],ax

                mov ax,ylaunch
                mov ts[si+ypos],ax
                sub ax,dx
                mov ts[si+deltay],ax

                mov ts[si+direction],-1

                mov ax,ts[si+deltay]
                sub ax,ts[si+deltax]
                sar ax,1
                mov ts[si+decision],ax

                cmp ts[si+deltax],0
                jl sturev
                jmp studone
        sturev:
                neg ts[si+deltax]
                neg ts[si+direction]
        studone:
                ret

starttracer     endp


startwarhead    proc near

                mov ax,lasttask
                cmp ax,maxtask
                jl swcd
                ret
        swcd:
                inc lasttask
                mov si,lasttask
                shl si,5
                mov ts[si+kind],1
                mov ax,warheadspeed
                mov ts[si+skip],ax
                mov ax,timer
                mov ts[si+time],ax
                mov ts[si+address],offset warhead

                cmp bx,-1
                jne swhsk1
                mov bx,0
                call random
                and ax,7
                shl ax,1
                mov bx,ax
        swhsk1:
                mov ts[si+target],bx
                mov bx,targetx[bx]

                cmp cx,-1
                jne swhsk2
                push bx
                mov bx,maxx
                inc bx
                call random
                mov cx,ax
                pop bx
        swhsk2:
                mov ts[si+xpos],cx
                mov ts[si+lastx],cx
                sub bx,cx
                mov ts[si+deltax],bx

                mov ts[si+ypos],dx
                mov ts[si+lasty],dx
                sub dx,citydeck
                neg dx
                mov ts[si+deltay],dx

                mov ts[si+direction],1

                mov ax,ts[si+deltay]
                sub ax,ts[si+deltax]
                sar ax,1
                mov ts[si+decision],ax
                mov ts[si+lastdec],ax

                mov ax,warheadcolor1
                mov ts[si+color1],ax
                mov ax,warheadcolor2
                mov ts[si+color2],ax
                cmp ts[si+deltax],0
                jl swhrev
                jmp swhdone
        swhrev:
                neg ts[si+deltax]
                neg ts[si+direction]
        swhdone:
                ret

startwarhead    endp


startsound      proc near

                mov ax,lasttask
                cmp ax,maxtask
                jl ssnd1
                ret
        ssnd1:
                shl bx,1
                inc lasttask
                mov si,lasttask
                shl si,5
                mov ts[si+kind],7
                mov ax,frequ0[bx]
                mov ts[si+skip],ax
                mov ax,frequ1[bx]
                mov ts[si+altskip],ax
                mov ax,timer
                mov ts[si+time],ax
                mov ts[si+address],offset sound

                in al,61h               ;disconnect speaker from timer
                and al,0feh
                out 61h,al
                or al,2
                mov ah,0
                mov ts[si+value],ax

                mov ax,frequc[bx]
                mov ts[si+cycles],ax

                ret

startsound      endp





