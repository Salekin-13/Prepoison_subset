library ieee; use ieee.std_logic_1164.all;
entity c4 is port (sel : in std_ulogic_vector(1 downto 0); a, b, c : in std_ulogic; q : out std_ulogic); end entity;
architecture x of c4 is begin
  with sel select q <=
    a when "00",
    b when "01" | "10",
    c when others;
end architecture;
