library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity e2 is port (a : in std_ulogic; l : linkage std_ulogic; q : out std_ulogic); end entity;
architecture x of e2 is begin q <= a; end architecture;
