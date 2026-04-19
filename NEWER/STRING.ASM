        ;string processing routines
        ;1-22-92  Joe Lowe
                dosseg
                model small
                public string_end,string_copy,string_cut,string_paste
                public int_to_string,string_to_int,string_out
                codeseg


proc            string_end

                ;returns offset of end of string and length of string not including
                ;  terminating zero

                ;call with:
                ;  ds:[si]=string
                ;returns:
                ;  ds:[di]=zero at end of string
                ;  cx=length

                push ax
                push es
                mov ax,ds
                mov es,ax
                sub al,al
                mov cx,-1
                mov di,si
                repnz scasb
                neg cx
                sub cx,2
                dec di
                pop es
                pop ax
                ret

endp


proc            string_copy

                ;copies string to destination

                ;call with:
                ;  ds:[si]=source string
                ;  ds:[di]=destination
                ;returns:
                ;  ds:[di]=terminating zero at destination

                push ax
                push si
                push es
                mov ax,ds
                mov es,ax
        cs_loop1:
                lodsb
                stosb
                or al,al
                jnz cs_loop1
                dec di
                pop es
                pop si
                pop ax
                ret

endp


proc            string_cut

                ;cuts portion of source string and copies it to target string
                ;
                ;call with:
                ;  cx=length of cut
                ;  ds:[si]=source string
                ;  ds:[di]=destination
                ;returns:
                ;  cx=length of cut (less than requested if zero found)
                ;  ds:[di]=terminating zero at destination

                push ax
                push bx
                push si
                push es

                mov ax,ds
                mov es,ax

                mov bx,cx
        sct_loop1:
                lodsb
                or al,al
                jz sct_out1
                stosb
                loop sct_loop1
        sct_out1:
                mov byte ptr es:[di],0

                sub bx,cx
                mov cx,bx

                pop es
                pop si
                pop bx
                pop ax
                ret

endp


proc            string_paste

                ;pastes source string into destination string
                ;
                ;call with:
                ;  ds:[si]=source string
                ;  ds:[di]=destination string
                ;returns:
                ;  ds:[di]=byte following last byte copied into destination string

                push ax
                push si
                push es
                mov ax,ds
                mov es,ax
                jmp sp_skip1
        sp_loop1:
                stosb
        sp_skip1:
                lodsb
                or al,al
                jnz cs_loop1
        sp_out1:
                pop es
                pop si
                pop ax
                ret

endp


proc            string_out

                ;writes string to stdout

                ;call with:
                ;  ds:[si]=zero terminated string

                push ax
                push bx
                push cx
                push dx
                push di

                call string_end
                mov dx,si
                mov ah,40h
                mov bx,1
                int 21h

                pop di
                pop dx
                pop cx
                pop bx
                pop ax
                ret

endp


proc            int_to_string

                ;converts integer to 5 digit ascii string

                ;call with:
                ;  ax=integer
                ;  ds:[di]=destination

                push ax
                push bx
                push cx
                push dx
                push di

                mov cx,ax
                mov ax,10000
                sub dx,dx
                mov bx,10
        its_loop1:
                mov byte ptr [di],'0'-1
        its_loop2:
                inc byte ptr [di]
                sub cx,ax
                ja its_loop2
                jz its_out1
                add cx,ax
                div bx
                inc di
                jmp short its_loop1
        its_out1:
                mov byte ptr [di+1],0

                pop di
                pop dx
                pop cx
                pop bx
                pop ax
                ret

endp


proc            string_to_int

                ;converts ascii digits to integer
                ;
                ;call with:
                ;  ds:[si]=string of ascii digits
                ;returns:
                ;  ax=integer

                push bx
                push cx
                push dx
                push si

                sub ax,ax               ;start with integer is zero
                mov bx,10               ;mul integer by ten after each new digit is found
                sub ch,ch               ;ch must be zero to add 8 bit digit to 16 bit integer
        sti_loop1:
                mov cl,[si]             ;get digit
                inc si                  ;point si to next point in array
                sub cl,'0'              ;make ascii into bcd
                cmp cl,9                ;is value over 9
                ja sti_out1             ;if so then non digit found so terminate
                mul bx                  ;multiply current integer by ten
                add ax,cx               ;add value of digit to integer
                jmp short sti_loop1     ;check next digit
        sti_out1:
                mov ax,cx

                pop si
                pop dx
                pop cx
                pop bx
                ret

endp


end
