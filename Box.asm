(LOOP)
    @KBD
    D=M
    @DRAW_BLACK
    D;JNE       
    @DRAW_WHITE
    0;JMP      
(DRAW_BLACK)
    @color
    M=-1       
    @DRAW_BOX
    0;JMP

(DRAW_WHITE)
    @color
    M=0        

(DRAW_BOX)
    @20
    D=A
    @rowCount
    M=D

    @16896
    D=A
    @rowAddr
    M=D

(ROW_LOOP)
    @rowCount
    D=M
    @LOOP
    D;JEQ

    @1
    D=A
    @wordCount
    M=D

    @rowAddr
    D=M
    @curAddr
    M=D

(WORD_LOOP)
    @wordCount
    D=M
    @NEXT_ROW
    D;JEQ

    @color
    D=M
    @curAddr
    A=M
    M=D

    @curAddr
    M=M+1

    @wordCount
    M=M-1

    @WORD_LOOP
    0;JMP

(NEXT_ROW)
    @32
    D=A
    @rowAddr
    M=D+M

    // rowCount--
    @rowCount
    M=M-1

    @ROW_LOOP
    0;JMP