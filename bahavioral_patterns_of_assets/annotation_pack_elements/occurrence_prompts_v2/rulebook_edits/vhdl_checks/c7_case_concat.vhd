library ieee; use ieee.std_logic_1164.all;
entity c7 is port (a, b, x, y : in std_ulogic; q : out std_ulogic); end entity;
architecture x of c7 is begin
  p: process (a, b, x, y) begin
    case std_ulogic_vector'(a & b) is
      when "00" => q <= x;
      when others => q <= y;
    end case;
  end process p;
end architecture;
