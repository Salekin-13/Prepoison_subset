library ieee; use ieee.std_logic_1164.all;
entity t5 is generic (EN : boolean := true); port (clk, d : in std_ulogic; q : out std_ulogic); end entity;
architecture a of t5 is
begin
  p: process (clk)
  begin
    g: if EN generate
      q <= d;
    end generate;
  end process p;
end architecture;
