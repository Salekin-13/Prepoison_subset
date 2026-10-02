library ieee; use ieee.std_logic_1164.all;
entity sub is generic (N : natural := 1); port (a : in std_ulogic; y : out std_ulogic); end entity;
architecture x of sub is begin y <= a; end architecture;
