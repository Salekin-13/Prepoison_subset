library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity d4 is port (a : in std_ulogic; q : out std_ulogic); end entity;
architecture x of d4 is begin
  p: process (a)
    signal s_proc : std_ulogic;
  begin
    q <= a;
  end process p;
end architecture;
