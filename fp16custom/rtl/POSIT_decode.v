module posit_decode #(parameter N = 10)(
    input  [N-1:0] p,
    output reg sign,
    output reg signed [5:0] k,     // Increased size to avoid overflow for large N
    output reg exp,
    output reg [N-4:0] frac        // Max fraction size is N-1-2-1 = N-4 bits. Wait. If N=8, N-4=4 bits. This matches es=1 perfectly.
);

reg [N-1:0] p_abs;
reg [N-2:0] mag;
reg regime_bit;
integer run, idx, i;
integer n_minus_2;

always @(*) begin
    n_minus_2 = N - 2;
    sign = p[N-1];
    k    = 0;
    exp  = 0;
    frac = 0;
    run  = 0;

    if (p == 0) begin
        sign = 0;
    end
    else if (p == (1 << (N-1))) begin // NaR is 1 followed by 0s
        sign = 1;
        k    = 0;
        exp  = 0;
        frac = 0;
    end
    else begin

        // full-word two's complement for negative posit
        if (sign)
            p_abs = (~p) + 1'b1;
        else
            p_abs = p;

        mag = p_abs[N-2:0];
        run=0;

        regime_bit = mag[N-2];

        begin : count_regime
            for (i = N-2; i >= 0; i = i - 1) begin
                if (mag[i] == regime_bit)
                    run = run + 1;
                else
                    disable count_regime;
            end
        end

        if (regime_bit)
            k = run - 1;
        else
            k = -run;

        if (run == N-1) begin
            exp  = 0;
            frac = 0;
        end
        else begin
            idx = n_minus_2 - run;   // move past regime
            idx = idx - 1;           // skip terminating bit
            
            // Only take exponent if space exists AFTER regime+terminator
            if (idx >= 0) begin
                exp = mag[idx];
                idx = idx - 1;
            end else begin
                exp = 0;
            end

            frac = 0;

            // Maximum fraction bits is N-4.
            for (i = 0; i <= N-4; i = i + 1) begin
                if (idx >= 0) begin
                    frac[(N-4) - i] = mag[idx];
                    idx = idx - 1;
                end
            end
        end
    end
end

endmodule