mothand         proc near

                mov ax,0bh
                int 33h
                mov ax,cx
                add ax,dx
                cmp ax,0
                je motdone
                call mouseoff
                shl cx,1
                shl dx,1
                add cx,mousex
                add dx,mousey
                cmp cx,cursminx
                jge motsk1
                mov cx,cursminx
        motsk1:
                cmp cx,cursmaxx
                jle motsk2
                mov cx,cursmaxx
        motsk2:
                cmp dx,cursminy
                jge motsk3
                mov dx,cursminy
        motsk3:
                cmp dx,cursmaxy
                jle motsk4
                mov dx,cursmaxy
        motsk4:
                mov mousex,cx
                mov mousey,dx
                call mouseon
        motdone:
                ret

mothand         endp


getbuttons      proc near


                push ax
                mov ax,3
                int 33h
                mov ax,0
                mov es,ax
                mov ax,es:[417h]
                shr ax,2
                and ax,3
                or bx,ax
                mov es,vidseg
                pop ax
                ret

getbuttons      endp


mouseon         proc near

                pusha

                mov ax,8
                mov cx,mousex
                mov dx,mousey
                mov si,cx
                mov di,dx
                sub cx,5
                sub dx,5
                add si,5
                add di,5
                call oline
                add dx,10
                sub di,10
                call oline

                popa
                ret

mouseon         endp


mouseoff        proc near

                pusha

                mov ax,7
                mov cx,mousex
                mov dx,mousey
                mov si,cx
                mov di,dx
                sub cx,5
                sub dx,5
                add si,5
                add di,5
                call aline
                add dx,10
                sub di,10
                call aline

                popa
                ret

mouseoff        endp


crosson         proc near

                pusha

                mov ax,mcolor2
                mov cx,mousex
                mov dx,mousey
                mov si,cx
                mov di,dx
                sub cx,5
                add si,5
                call line
                sub si,5
                add cx,5
                sub dx,5
                add di,5
                call line

                popa
                ret

crosson         endp
