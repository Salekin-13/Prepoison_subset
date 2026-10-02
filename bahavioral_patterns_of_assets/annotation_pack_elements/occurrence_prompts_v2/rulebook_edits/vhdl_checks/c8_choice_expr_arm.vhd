library ieee; use ieee.std_logic_1164.all;
entity c8 is port (sel : in std_ulogic_vector(1 downto 0); a, b, c : in std_ulogic; q : out std_ulogic); end entity;
architecture x of c8 is begin
  with sel select q <= a and b when "00", not c when others;
end architecture;
