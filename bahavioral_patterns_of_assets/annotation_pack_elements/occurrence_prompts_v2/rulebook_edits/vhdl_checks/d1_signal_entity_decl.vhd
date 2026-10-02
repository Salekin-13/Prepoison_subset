library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity d1 is port (a : in std_ulogic; q : out std_ulogic);
  signal s_ent : std_ulogic;
end entity;
architecture x of d1 is begin q <= a; end architecture;
