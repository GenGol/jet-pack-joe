                title
                dosseg
                .model small
                .286
                .stack
                .code

proc            main

                mov ax,@data
                mov ds,ax

                mov bx,offset ref_set0
                call get_regs
        init1:
                sub ah,ah
                mov al,[get_mod]
                int 10h
                mov bx,offset mod_set
                call get_regs
        init2:
                sub ah,ah
                mov al,[ref_mode]
                int 10h
                mov bx,offset ref_set1
                call get_regs

                call do_screen

                call move_cursor
        loop1:
                mov ah,10h
                int 16h

                cmp ah,77
                je point1
                cmp ah,80
                jne skip1
        point1:
                inc marker
                cmp marker,44
                jle skip1
                mov marker,0
        skip1:
                cmp ah,75
                je point2
                cmp ah,72
                jne skip2
        point2:
                dec marker
                cmp marker,0
                jge skip2
                mov marker,44
        skip2:
                cmp ah,28
                jne skip3
                cmp marker,43
                jne skip2a
                jmp init2
        skip2a:
                cmp marker,44
                jne skip2b
                mov al,get_mod
                sub ah,ah
                int 10h
                mov bx,offset mod_set
                call get_regs
                call do_screen

                jmp init1
        skip2b:
                mov bx,offset mod_set
                call set_regs
                mov ah,0
                int 16h
                call do_screen
        skip3:
                cmp ah,12
                jne skip4
                mov bx,marker
                dec mod_set[bx]
                jmp point4
        skip4:
                cmp ah,13
                jne skip5
                mov bx,marker
                inc mod_set[bx]
                jmp point4
        skip5:
                cmp al,48
                jl skip6
                cmp al,57
                jg skip6
                sub al,48
                jmp point3
        skip6:
                cmp al,65
                jl skip7
                cmp al,70
                jg skip7
                sub al,55
                jmp point3
        skip7:
                cmp al,97
                jl skip8
                cmp al,102
                jg skip8
                sub al,87
        point3:
                mov bx,marker
                shl mod_set[bx],4
                add mod_set[bx],al
        point4:
                mov bx,offset mod_set
                mov dx,offset registers+7
                call paste_values
                call draw_screen
                jmp loop1
        skip8:
                cmp ah,1
                je done

                call move_cursor
                jmp loop1
        done:
                mov ax,4c00h
                int 21h

endp


proc            do_screen

                push bx
                push dx

                call set_mode

                mov bx,offset ref_set0
                mov dx,offset registers+1
                call paste_values

                mov bx,offset ref_set1
                mov dx,offset registers+4
                call paste_values

                mov bx,offset mod_set
                mov dx,offset registers+7
                call paste_values

                call draw_screen

                pop dx
                pop bx
                ret

endp


proc            set_mode

                mov ax,3
                int 10h

                mov ax,1112h
                mov bl,0
                int 10h

                ret

endp


proc            get_regs

                push ax
                push dx
                push di
                push es

                mov dx,ds
                mov es,dx
                mov di,bx

                mov dx,3cch             ;miscellaneous out reg
                in al,dx
                stosb

                mov dx,3c4h             ;sequencer regs 1-4
                mov ah,1
        gr_loop1:
                mov al,ah
                cli
                out dx,al
                inc dx
                in al,dx
                sti
                dec dx
                stosb
                inc ah
                cmp ah,4
                jle gr_loop1

                mov dx,3d4h             ;crtc regs 0-18h
                mov ah,0
        gr_loop2:
                mov al,ah
                cli
                out dx,al
                inc dx
                in al,dx
                sti
                dec dx
                stosb
                inc ah
                cmp ah,18h
                jle gr_loop2

                mov dx,3ceh             ;graphics controller regs 0-8
                mov ah,0
        gr_loop3:
                mov al,ah
                cli
                out dx,al
                inc dx
                in al,dx
                sti
                dec dx
                stosb
                inc ah
                cmp ah,8
                jle gr_loop3

                mov ah,10h              ;attribute controller regs 10h-13h
        gr_loop4:
                mov dx,3dah
                in al,dx
                mov dx,3c0h
                mov al,ah
                cli
                out dx,al
                inc dx
                in al,dx
                sti
                stosb
                inc ah
                cmp ah,13h
                jle gr_loop4

                mov dx,3dah
                in al,dx
                mov dx,3c0h
                mov al,32
                out dx,al

                pop es
                pop di
                pop dx
                pop ax
                ret

endp


proc            set_regs

                push ax
                push dx
                push si

                mov si,bx

                mov dx,3c2h             ;miscellaneous out reg
                lodsb
                out dx,al

                mov dx,3c4h             ;sequencer regs 1-4
                mov ah,1
        sr_loop1:
                lodsb
                xchg ah,al
                out dx,ax
                xchg ah,al
                inc ah
                cmp ah,4
                jle sr_loop1

                mov dx,3d4h             ;crtc regs 0-18h
                mov ax,0011h
                out dx,ax
                mov ah,0
        sr_loop2:
                lodsb
                xchg ah,al
                out dx,ax
                xchg ah,al
                inc ah
                cmp ah,18h
                jle sr_loop2

                mov dx,3ceh             ;graphics controller regs 0-8
                mov ah,0
        sr_loop3:
                lodsb
                xchg ah,al
                out dx,ax
                xchg ah,al
                inc ah
                cmp ah,8
                jle sr_loop3

                mov ah,10h              ;attribute controller regs 10h-13h
        sr_loop4:
                mov dx,3dah
                in al,dx
                mov dx,3c0h
                mov al,ah
                cli
                out dx,al
                lodsb
                out dx,al
                sti
                inc ah
                cmp ah,13h
                jle sr_loop4

                mov dx,3dah
                in al,dx
                mov dx,3c0h
                mov al,32
                out dx,al

                pop si
                pop dx
                pop ax
                ret

endp


proc            paste_values

                push ax
                push bx
                push cx
                push si

                mov cx,43
                mov si,dx
        pv_loop1:
                mov al,[bx]
                inc bx
                call paste_hex
                add si,40
                loop pv_loop1

                pop si
                pop cx
                pop bx
                pop ax
                ret

endp


proc            draw_screen

                push ax
                push cx
                push dx
                push si
                push es

                mov ax,0b800h
                mov es,ax

                mov di,0
                mov cx,4000
                mov ax,0720h
                rep stosw

                mov cx,43
                mov dx,0514h
                mov si,offset registers
        ds_loop1:
                call video
                inc dh
                add si,40
                loop ds_loop1

                mov si,offset temp+1
                mov al,ref_mode
                call paste_hex
                mov si,offset temp
                mov dx,0317h
                call video
                mov si,offset temp+1
                mov al,get_mod
                call paste_hex
                mov si,offset temp
                mov dx,031ah
                call video

                pop es
                pop si
                pop dx
                pop cx
                pop ax
                ret

endp


proc            video

                ;call with:
                ;  ds:si=offset of text
                ;  dh,dl=row,column

                push ax
                push bx
                push cx
                push dx
                push bp
                push es

                mov bp,si
                inc bp
                mov ax,ds
                mov es,ax
                mov ax,1300h
                mov cl,[si]
                sub ch,ch
                mov bx,0007h
                int 10h

                pop es
                pop bp
                pop dx
                pop cx
                pop bx
                pop ax
                ret

endp


proc            paste_hex

                ;call with:
                ;  al=8 bit number
                ;  ds:si=destination

                push ax

                mov ah,al
                shr al,1
                shr al,1
                shr al,1
                shr al,1
                and ax,0f0fh
                cmp ah,9
                jle ph_skip1
                add ah,7
        ph_skip1:
                cmp al,9
                jle ph_skip2
                add al,7
        ph_skip2:
                add ax,3030h
                mov [si],ax

                pop ax
                ret

endp


proc            move_cursor

                push ax
                push bx
                push dx

                mov bx,marker
                shl bx,1
                mov dx,mark_loc[bx]
                sub bh,bh
                mov ah,2
                int 10h

                pop dx
                pop bx
                pop ax
                ret

endp


                .data


marker          dw 0

mark_loc        label word
                dw 051bh,061bh,071bh,081bh,091bh,0a1bh,0b1bh,0c1bh
                dw 0d1bh,0e1bh,0f1bh,101bh,111bh,121bh,131bh,141bh
                dw 151bh,161bh,171bh,181bh,191bh,1a1bh,1b1bh,1c1bh
                dw 1d1bh,1e1bh,1f1bh,201bh,211bh,221bh,231bh,241bh
                dw 251bh,261bh,271bh,281bh,291bh,2a1bh,2b1bh,2c1bh
                dw 2d1bh,2e1bh,2f1bh,0318h,031bh




registers       label byte
                db 39,"          Miscellaneous Output         "
                db 39,"          Clock Mode                   "
                db 39,"          Map Mask                     "
                db 39,"          Character Map Select         "
                db 39,"          Memory Mode                  "
                db 39,"          Horizontal Total             "
                db 39,"          Horizontal Display Enable End"
                db 39,"          Start Horizontal Blanking    "
                db 39,"          End Horizontal Blanking      "
                db 39,"          Start Horizontal Retrace     "
                db 39,"          End Horizontal Retrace       "
                db 39,"          Vertical Total               "
                db 39,"          CRTC Overflow                "
                db 39,"          Preset Row Scan              "
                db 39,"          Max Scan Line                "
                db 39,"          Cursor Start                 "
                db 39,"          Cursor End                   "
                db 39,"          Start Address High           "
                db 39,"          Start Address Low            "
                db 39,"          Cursor Location High         "
                db 39,"          Cursor Location Low          "
                db 39,"          Vertical Retrace Start       "
                db 39,"          Vertical Retrace End         "
                db 39,"          Vertical Display Enable End  "
                db 39,"          Offset                       "
                db 39,"          Underline Location           "
                db 39,"          Start Vertical Blanking      "
                db 39,"          End Vertical Blanking        "
                db 39,"          Mode Control                 "
                db 39,"          Line Compare                 "

                db 39,"          Set/Reset                    "
                db 39,"          Enable Set/Reset             "
                db 39,"          Color Compare                "
                db 39,"          Data Rotate                  "
                db 39,"          Read Map Select              "
                db 39,"          Mode                         "
                db 39,"          Miscellaneous                "
                db 39,"          Color Don't Care             "
                db 39,"          Bit Mask                     "
                db 39,"          Mode Control                 "
                db 39,"          Overscan                     "
                db 39,"          Color Plane Enable           "
                db 39,"          Horizontal Pixel Panning     "


mod_set         db 43 dup(97h)
ref_mode        db 03h
get_mod         db 03h
ref_set0        db 43 dup(11h)
ref_set1        db 43 dup(43h)
temp            db 2,"  "


end































