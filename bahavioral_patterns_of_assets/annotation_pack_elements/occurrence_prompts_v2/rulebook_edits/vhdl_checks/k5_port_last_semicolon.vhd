library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity k5 is port (a : in std_ulogic; q : out std_ulogic;); end entity;
architecture x of k5 is begin q <= a; end architecture;
