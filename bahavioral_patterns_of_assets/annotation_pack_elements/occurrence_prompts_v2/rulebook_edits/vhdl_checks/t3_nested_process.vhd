library ieee; use ieee.std_logic_1164.all;
entity t3 is port (clk : in std_ulogic; d : in std_ulogic; q : out std_ulogic); end entity;
architecture a of t3 is
begin
  p_outer: process (clk)
  begin
    p_inner: process (clk)
    begin
      q <= d;
    end process p_inner;
  end process p_outer;
end architecture;
