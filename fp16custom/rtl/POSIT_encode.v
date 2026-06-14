module posit_encode #(parameter N = 10)(
    input        sign,
    input signed [5:0] k,
    input        exp,
    input  [N-4:0] frac,
    input        nar,
    input        zero,
    output reg [N-1:0] p
);

reg [N-1:0] temp;
integer idx;
integer i;
integer n_minus_2;

always @(*) begin
    n_minus_2 = N - 2;
    // defaults
    p    = 0;
    temp = 0;

    // special cases
    if (zero)
        p = 0;
    else if (nar)
        p = (1 << (N-1));
    else if (k >= (N-2)) begin
        p = sign ? ((1 << (N-1)) | 1) : ((1 << (N-1)) - 1); // saturate min/max
    end
    else if (k <= -(N-2)) begin
        p = sign ? ((1 << N) - 1) : 1; // minpos / -minpos
    end
    else begin

        idx = n_minus_2;

        // regime
        if (k >= 0) begin
            // write k+1 ones
            for (i=0; i<k+1 && idx>=0; i=i+1) begin
                temp[idx] = 1'b1;
                idx = idx - 1;
            end

            // terminating zero
            if (idx >= 0) begin
                temp[idx] = 1'b0;
                idx = idx - 1;
            end
        end
        else begin
            // write -k zeros
            for (i=0; i<(-k) && idx>=0; i=i+1) begin
                temp[idx] = 1'b0;
                idx = idx - 1;
            end

            // terminating one
            if (idx >= 0) begin
                temp[idx] = 1'b1;
                idx = idx - 1;
            end
        end

        // exponent
        if (idx >= 0) begin
            temp[idx] = exp;
            idx = idx - 1;
        end

        // fraction bits
        for (i = 0; i <= N-4; i = i + 1) begin
            if (idx >= 0) begin
                temp[idx] = frac[(N-4) - i];
                idx = idx - 1;
            end
        end

        // apply sign
        if (sign)
            p = ((~temp) + 1'b1) & ((1 << N) - 1);
        else
            p = temp;
    end
end

endmodule