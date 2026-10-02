library ieee; use ieee.std_logic_1164.all;
entity d8 is port (a : in std_ulogic; q : out std_ulogic); end entity;
architecture x of d8 is begin
  p: process (a)
    variable v : std_ulogic;
  begin
    v := not a; q <= v;
  end process p;
end architecture;
