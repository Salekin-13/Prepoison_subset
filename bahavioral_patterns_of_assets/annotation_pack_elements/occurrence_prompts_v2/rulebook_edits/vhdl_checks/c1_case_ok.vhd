library ieee; use ieee.std_logic_1164.all;
entity c1 is port (clk : in std_ulogic; sel : in std_ulogic_vector(1 downto 0); a, b, c : in std_ulogic; q : out std_ulogic); end entity;
architecture x of c1 is begin
  p: process (clk) begin
    if rising_edge(clk) then
      case sel is
        when "00" => q <= a;
        when "01" | "10" => q <= b;
        when others => q <= c;
      end case;
    end if;
  end process p;
end architecture;
