module posit_encode #(
    parameter N = 10,
    parameter W_FRAC = N-3
)(
    input        sign,
    input signed [5:0] k,
    input        exp,
    input  [W_FRAC-1:0] frac,
    input        nar,
    input        zero,
    output reg [N-1:0] p
);

reg [N-1:0] rounded_p;
reg round_up;
integer n_minus_2;

reg [N-2:0] regime_val;
reg [W_FRAC+4:0] payload_padded;
reg [5:0] shift_amt;
reg [N+W_FRAC+5:0] regime_word;
reg [N+W_FRAC+5:0] payload_word;
reg [N+W_FRAC+5:0] combined;
reg [N-1:0] unrounded_p;
reg LSB;
reg round;
reg sticky;

always @(*) begin
    rounded_p = 0;
    round_up  = 0;
    n_minus_2 = N - 2;

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
        // Regime value generation using shift-and-mask (no loops)
        // If k >= 0: regime is (k+1) ones followed by a 0.
        // If k < 0: regime is (-k) zeros followed by a 1.
        // We construct a mask of N-1 bits
        regime_val = (k >= 0) ? ~({(N-1){1'b1}} >> (k+1)) : (1'b1 << (N-2+k));
        
        // Payload consists of exponent and fraction
        payload_padded = {exp, frac, 4'b0};
        
        // Payload shift amount
        shift_amt = (k >= 0) ? (k + 2) : (-k + 1);
        
        // Combine regime and payload into a wide word
        regime_word = { regime_val, {W_FRAC+7{1'b0}} };
        payload_word = { payload_padded, {(N+1){1'b0}} } >> shift_amt;
        combined = regime_word | payload_word;
        
        // Extract unrounded value and rounding bits
        unrounded_p = {1'b0, combined[N+W_FRAC+5 : W_FRAC+7]};
        LSB = combined[W_FRAC+7];
        round = combined[W_FRAC+6];
        sticky = |combined[W_FRAC+5 : 0];
        
        round_up = round && (LSB || sticky);
        
        if (round_up) begin
            rounded_p = unrounded_p + 1'b1;
            // Clamping on overflow to NaR (avoid sign bit or NaR representation)
            if (rounded_p[N-1] && ~unrounded_p[N-1]) begin
                rounded_p = (1 << (N-1)) - 1;
            end
        end
        else begin
            rounded_p = unrounded_p;
        end

        // apply sign
        if (sign)
            p = ((~rounded_p) + 1'b1) & ((1 << N) - 1);
        else
            p = rounded_p;
    end
end

endmodule