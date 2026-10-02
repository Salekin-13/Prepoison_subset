library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity e1 is port (clk, d : in std_ulogic; q : out std_ulogic); end entity;
architecture x of e1 is begin
  p_lab: process (clk)
  begin
    if rising_edge(clk) then q <= d; end if;
  end process;
end architecture;
