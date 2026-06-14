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

reg [N-2:0] shifted_mag;
reg [5:0] run_reg;
reg found_reg;

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
        run = 0;
        regime_bit = mag[N-2];

        // Loop-free count using a synthesizable priority encoder tree
        run_reg = N - 1;
        found_reg = 0;
        for (i = 0; i < N - 1; i = i + 1) begin
            if (!found_reg && (mag[N-2 - i] != regime_bit)) begin
                run_reg = i;
                found_reg = 1;
            end
        end

        run = run_reg;

        if (regime_bit)
            k = run - 1;
        else
            k = -run;

        if (run == N-1) begin
            exp  = 0;
            frac = 0;
        end
        else begin
            // Extract exp and frac using a single barrel shifter
            shifted_mag = mag << (run + 1);
            
            exp = shifted_mag[N-2];
            frac = shifted_mag[N-3 : 1]; // Keep exactly N-3 bits (matches [N-4:0] width)
        end
    end
end

endmodule