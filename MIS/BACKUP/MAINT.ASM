
cloud           proc near

                cmp ts[si+direction],0
                jle cldown
        clup:
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                mov bx,ts[si+radius]
                mov ax,ts[si+color]
                call circle
                cmp bx,ts[si+maxradius]
                jge cluptdn
                inc ts[si+radius]
                ret
        cluptdn:
                neg ts[si+direction]
                ret
        cldown:
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                mov bx,ts[si+radius]
                mov ax,backcolor
                call circle
                dec ts[si+radius]
                cmp bx,0
                jg cldone
                call endtask
        cldone:
                ret

cloud           endp


upmissile       proc near

                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                mov ax,ts[si+color2]
                call plot
                cmp ts[si+decision],0
                jl umhoriz
        umvert:
                dec ts[si+ypos]
                mov ax,ts[si+deltax]
                sub ts[si+decision],ax
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                mov ax,ts[si+color1]
                call plot
                jmp umdone
        umhoriz:
                mov ax,ts[si+direction]
                add ts[si+xpos],ax
                mov ax,ts[si+deltay]
                add ts[si+decision],ax
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                mov ax,ts[si+color1]
                call plot
        umdone:
                cmp dx,ts[si+lasty]
                jg umska
                cmp ts[si+direction],0
                jg umskb
                cmp cx,ts[si+lastx]
                jle umend
        umska:
                ret
        umskb:
                cmp cx,ts[si+lastx]
                jge umend
                ret
        umend:
                mov ax,cloudcolor
                call startcloud
                call endtask
                ret

upmissile       endp


tracer          proc near

                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                call get
                and al,7
                cmp al,byte ptr mcolor2
                jne trsk1
                mov ax,backcolor
                call plot
        trsk1:
                cmp ts[si+decision],0
                jl trhoriz
        trvert:
                dec ts[si+ypos]
                mov ax,ts[si+deltax]
                sub ts[si+decision],ax
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                jmp trdone
        trhoriz:
                mov ax,ts[si+direction]
                add ts[si+xpos],ax
                mov ax,ts[si+deltay]
                add ts[si+decision],ax
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
        trdone:
                cmp dx,ts[si+lasty]
                jg trska
                cmp ts[si+direction],0
                jg trskb
                cmp cx,ts[si+lastx]
                jle trend
        trska:
                ret
        trskb:
                cmp cx,ts[si+lastx]
                jge trend
                ret
        trend:
                call endtask
                ret

tracer          endp


warhead         proc near

                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                mov ax,ts[si+color2]
                call plot
                cmp ts[si+decision],0
                jge whvert
                jmp whhoriz
        whvert:
                inc ts[si+ypos]
                mov ax,splitdeck
                cmp ts[si+ypos],ax
                je whsk4
                jmp whsk2
        whsk4:
                mov bx,0
                call random
                and ax,3
                je whsk5
                jmp whsk2
        whsk5:
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                mov bx,ts[si+target]
                add bx,2
                cmp bx,14
                jle whska
                sub bx,6
        whska:
                pusha
                call startwarhead
                popa
                mov bx,ts[si+target]
                sub bx,2
                cmp bx,0
                jge whskb
                add bx,6
        whskb:
                pusha
                call startwarhead
                popa
        whsk3:
               ;mov cx,ts[si+xpos]
               ;mov dx,ts[si+ypos]
               ;xchg cx,ts[si+lastx]
               ;xchg dx,ts[si+lasty]
               ;mov ts[si+xpos],cx
               ;mov ts[si+ypos],dx
               ;mov ax,ts[si+lastdec]
               ;mov ts[si+decision],ax
               ;mov ts[si+address],offset wartrace
               ;mov ts[si+kind],5
               ;mov ax,wartracespeed
               ;mov ts[si+skip],ax
               ;jmp whdone
        whsk2:
                mov ax,maxy-15
                cmp ts[si+ypos],ax
                jg whsk9
                mov ax,ts[si+deltax]
                sub ts[si+decision],ax
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                call get
                and ax,7
                cmp ax,4
                jl whsk1
                cmp ax,cloudcolor
                jne whsk7
                mov ax,points1
                call upscore
        whsk7:
                cmp ax,warcloudcolor
                jne whsk8
                mov ax,points2
                call upscore
        whsk8:
                cmp ax,citycolor
                jne whsk9
                jmp whcity
        whsk9:
                push si
                mov ax,warcloudcolor
                call startcloud
                mov bx,1
                call startsound
                pop si
        whsk10:
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                xchg cx,ts[si+lastx]
                xchg dx,ts[si+lasty]
                mov ts[si+xpos],cx
                mov ts[si+ypos],dx
                mov ax,ts[si+lastdec]
                mov ts[si+decision],ax
                mov ts[si+address],offset wartrace
                mov ts[si+kind],5
                mov ax,wartracespeed
                mov ts[si+skip],ax
                jmp whdone
        whsk1:
                mov ax,ts[si+color1]
                call plot
                jmp whdone
        whhoriz:
                mov ax,ts[si+direction]
                add ts[si+xpos],ax
                mov ax,ts[si+deltay]
                add ts[si+decision],ax
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                mov ax,ts[si+color1]
                call plot
        whdone:
                ret
        whcity:
                mov bx,10
        whc1:
                mov ax,cityx[bx]
                cmp ax,cx
                jle whc2
                sub bx,2
                je whc2
                jmp whc1
        whc2:
                inc cityhits[bx]
                shr bx,1
                call nukecity
                jmp whsk10

warhead         endp


wartrace        proc near

                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                call get
                and ax,7
                cmp ax,warheadcolor2
                jne wtsk1
                mov ax,backcolor
                call plot
        wtsk1:
                cmp ts[si+decision],0
                jl wthoriz
        wtvert:
                inc ts[si+ypos]
                mov ax,ts[si+deltax]
                sub ts[si+decision],ax
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
                jmp wtdone
        wthoriz:
                mov ax,ts[si+direction]
                add ts[si+xpos],ax
                mov ax,ts[si+deltay]
                add ts[si+decision],ax
                mov cx,ts[si+xpos]
                mov dx,ts[si+ypos]
        wtdone:
                cmp dx,ts[si+lasty]
                jl wtska
                cmp ts[si+direction],0
                jg wtskb
                cmp cx,ts[si+lastx]
                jle wtend
        wtska:
                ret
        wtskb:
                cmp cx,ts[si+lastx]
                jge wtend
                ret
        wtend:
                call endtask
                ret

wartrace        endp


sound           proc near

                mov ax,ts[si+value]
                xor ts[si+value],2
                out 61h,al
                dec ts[si+cycles]
                cmp ts[si+cycles],0
                jle snddone
                mov ax,ts[si+altskip]
                xchg ts[si+skip],ax
                mov ts[si+altskip],ax
                ret
        snddone:
                call endtask
                ret

sound           endp


