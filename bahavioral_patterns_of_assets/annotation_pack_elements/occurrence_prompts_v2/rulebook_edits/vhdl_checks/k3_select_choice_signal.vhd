library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity k3 is port (sel, other : in std_ulogic_vector(1 downto 0); a, b : in std_ulogic; q : out std_ulogic); end entity;
architecture x of k3 is begin
  with sel select q <= a when other, b when others;
end architecture;
